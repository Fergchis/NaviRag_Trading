import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from agent_app.agent import graph
from src.config import APP_NAME, ORGANIZATION


def message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def final_answer(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return message_text(message.content)
    return ""


def render_assistant_diagnostics(message: dict) -> None:
    diagnostics = message.get("diagnostics")
    if not diagnostics:
        return

    with st.expander("Detalles técnicos"):
        st.write(f"Ruta: {diagnostics['route']}")
        st.write(
            "Agentes ejecutados: "
            + (", ".join(diagnostics["executed_agents"]) or "-")
        )
        st.write(f"Agente final: {diagnostics['final_agent']}")
        st.write(f"Retrieval: {'sí' if diagnostics['retrieval_used'] else 'no'}")
        st.write(f"Memoria: {'sí' if diagnostics['memory_used'] else 'no'}")
        st.write(
            "Rechazo financiero seguro: "
            f"{'sí' if diagnostics['financial_rejection'] else 'no'}"
        )

        if diagnostics["retrieved_context"]:
            st.divider()
            st.caption("Fuentes y contexto recuperado")
            st.text(diagnostics["retrieved_context"])


st.set_page_config(page_title=APP_NAME)
st.title(APP_NAME)
st.caption(f"Demo educativa para {ORGANIZATION}")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.caption(f"Sesión: `{st.session_state.thread_id[:8]}...`")
    if st.button("Nueva conversación", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.rerun()
    st.divider()
    st.caption("El diagnóstico técnico está disponible en cada respuesta.")

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_assistant_diagnostics(message)

if query := st.chat_input("Pregunta sobre los PDFs de trading..."):
    st.session_state.chat_history.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            try:
                result = graph.invoke(
                    {"messages": [HumanMessage(content=query)]},
                    config={
                        "configurable": {
                            "thread_id": st.session_state.thread_id,
                            "user_id": st.session_state.user_id,
                        }
                    },
                )
            except Exception as exc:
                err_name = type(exc).__name__.lower()
                err_text = str(exc).lower()
                if (
                    "ratelimit" in err_name
                    or "rate limit" in err_text
                    or "too many requests" in err_text
                ):
                    st.error(
                        "El proveedor del modelo está limitado temporalmente. "
                        "Espera unos minutos o revisa el token configurado."
                    )
                else:
                    st.error(
                        "No se pudo generar la respuesta. Revisa la configuración "
                        "del entorno o intenta nuevamente."
                    )
                st.stop()

        answer = final_answer(result["messages"])
        diagnostics = {
            "route": result.get("next", "unknown"),
            "executed_agents": result.get("executed_agents", []),
            "final_agent": result.get("final_agent", "unknown"),
            "retrieval_used": bool(result.get("retrieval_used", False)),
            "memory_used": bool(result.get("memory_used", False)),
            "financial_rejection": bool(
                result.get("financial_rejection", False)
            ),
            "retrieved_context": result.get("retrieved_context", ""),
        }

        st.markdown(answer)
        render_assistant_diagnostics({"diagnostics": diagnostics})

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer,
        "diagnostics": diagnostics,
    })
