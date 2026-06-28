import os
import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent_app.agent import graph
from src.config import APP_NAME, ORGANIZATION
from src.observability import SupabaseLogger


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


def _get_company(model: str) -> str:
    provider, _, model_name = model.partition("/")
    normalized_model = model_name or model
    if provider == "openai" or normalized_model.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    if provider == "anthropic" or normalized_model.startswith("claude"):
        return "anthropic"
    return provider or "unknown"


def _get_model_name(model: str) -> str:
    _, _, model_name = model.partition("/")
    return model_name or model


def _record_observability_error(exc: Exception) -> None:
    if "observability_errors" not in st.session_state:
        st.session_state.observability_errors = []
    st.session_state.observability_errors.append({
        "error_type": type(exc).__name__,
        "error": str(exc),
    })


def _safe_observability_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        _record_observability_error(exc)
        return None


def _get_observability_logger() -> SupabaseLogger | None:
    if "observability_logger" in st.session_state:
        return st.session_state.observability_logger

    try:
        st.session_state.observability_logger = SupabaseLogger()
        return st.session_state.observability_logger
    except Exception as exc:
        _record_observability_error(exc)
        return None


def _get_or_create_observability_session() -> str | None:
    logger = _get_observability_logger()
    if logger is None:
        return None

    if st.session_state.get("observability_thread_id") != st.session_state.thread_id:
        st.session_state.pop("observability_session_id", None)
        st.session_state.observability_thread_id = st.session_state.thread_id

    if "observability_session_id" not in st.session_state:
        session_id = _safe_observability_call(
            logger.create_session,
            thread_id=st.session_state.thread_id,
            user_id=st.session_state.user_id,
        )
        if session_id:
            st.session_state.observability_session_id = session_id

    return st.session_state.get("observability_session_id")


def _iter_stream_chunk(chunk):
    if isinstance(chunk, dict):
        return chunk.items()
    return [(
        "stream_event",
        {
            "raw_event_type": type(chunk).__name__,
            "raw_event": str(chunk),
        },
    )]


def _extract_trace_payload(node_name: str, state, query: str) -> dict:
    tool_name = None
    input_data = {"content": query}
    output_data = {}
    prompt_tokens = None
    completion_tokens = None

    if not isinstance(state, dict):
        output_data["state_type"] = type(state).__name__
        output_data["state_preview"] = str(state)
        return {
            "tool_name": tool_name,
            "input": input_data,
            "output": output_data,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    if "raw_event_type" in state:
        output_data.update(state)

    for key in (
        "next",
        "executed_agents",
        "retrieval_used",
        "memory_used",
        "financial_rejection",
        "user_query",
    ):
        if key in state:
            output_data[key] = state.get(key)

    messages = state.get("messages", [])

    for msg in messages if isinstance(messages, list) else []:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            tool_name = msg.tool_calls[0]["name"] if len(msg.tool_calls) == 1 else None
            output_data["tool_calls"] = [
                {"name": call["name"], "args": call.get("args", {})}
                for call in msg.tool_calls
            ]
        elif isinstance(msg, ToolMessage):
            tool_name = msg.name
            content = message_text(msg.content)
            chunks = content.split("\n\n") if content else []
            output_data["chunks_count"] = len(chunks)
            output_data["chunks"] = chunks
            output_data["full_result"] = content
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            output_data["content"] = message_text(msg.content)

        usage_metadata = getattr(msg, "usage_metadata", None)
        if isinstance(msg, AIMessage) and usage_metadata:
            prompt_tokens = usage_metadata.get("input_tokens")
            completion_tokens = usage_metadata.get("output_tokens")

    return {
        "tool_name": tool_name,
        "input": input_data,
        "output": output_data,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def _log_stream_error(
    logger: SupabaseLogger | None,
    session_id: str | None,
    message_id: str | None,
    step_order: int,
    node_start,
    query: str,
    exc: Exception,
) -> None:
    if logger is None or session_id is None or message_id is None:
        return

    node_end = SupabaseLogger.now()
    _safe_observability_call(
        logger.log_trace,
        session_id=session_id,
        message_id=message_id,
        step_order=step_order,
        node_name="stream_error",
        started_at=node_start,
        ended_at=node_end,
        input={"content": query},
        output={
            "error_type": type(exc).__name__,
            "error": str(exc),
        },
    )


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
        st.write(f"Retrieval: {'sí' if diagnostics['retrieval_used'] else 'no'}")
        st.write(f"Memoria: {'sí' if diagnostics['memory_used'] else 'no'}")
        st.write(
            "Rechazo financiero seguro: "
            f"{'sí' if diagnostics['financial_rejection'] else 'no'}"
        )



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
        st.session_state.pop("observability_session_id", None)
        st.session_state.pop("observability_thread_id", None)
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
            observability_logger = _get_observability_logger()
            observability_session_id = _get_or_create_observability_session()
            message_id = None
            if observability_logger is not None and observability_session_id is not None:
                message_id = _safe_observability_call(
                    observability_logger.log_message,
                    observability_session_id,
                    "user",
                    query,
                )

            config = {
                "configurable": {
                    "thread_id": st.session_state.thread_id,
                    "user_id": st.session_state.user_id,
                }
            }
            configured_model = os.getenv("GITHUB_CHAT_MODEL", "openai/gpt-4o-mini")
            company = _get_company(configured_model)
            model = _get_model_name(configured_model)
            step_order = 0
            node_start = SupabaseLogger.now()
            try:
                for chunk in graph.stream(
                    {"messages": [HumanMessage(content=query)]},
                    config=config,
                    stream_mode="updates",
                ):
                    node_end = SupabaseLogger.now()
                    for node_name, state in _iter_stream_chunk(chunk):
                        payload = _extract_trace_payload(node_name, state, query)
                        trace_id = None
                        if (
                            observability_logger is not None
                            and observability_session_id is not None
                            and message_id is not None
                        ):
                            trace_id = _safe_observability_call(
                                observability_logger.log_trace,
                                session_id=observability_session_id,
                                message_id=message_id,
                                step_order=step_order,
                                node_name=node_name,
                                tool_name=payload["tool_name"],
                                started_at=node_start,
                                ended_at=node_end,
                                input=payload["input"],
                                output=payload["output"],
                                prompt_tokens=payload["prompt_tokens"],
                                completion_tokens=payload["completion_tokens"],
                                company=company,
                                model=model,
                            )

                            if (
                                trace_id is not None
                                and payload["prompt_tokens"] is not None
                                and payload["completion_tokens"] is not None
                            ):
                                _safe_observability_call(
                                    observability_logger.log_cost,
                                    session_id=observability_session_id,
                                    message_id=message_id,
                                    trace_id=trace_id,
                                    company=company,
                                    model=model,
                                    prompt_tokens=payload["prompt_tokens"],
                                    completion_tokens=payload["completion_tokens"],
                                )

                        step_order += 1
                    node_start = node_end

                result = graph.get_state(config).values
            except Exception as exc:
                _log_stream_error(
                    observability_logger,
                    observability_session_id,
                    message_id,
                    step_order,
                    node_start,
                    query,
                    exc,
                )
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
            "retrieval_used": bool(result.get("retrieval_used", False)),
            "memory_used": bool(result.get("memory_used", False)),
            "financial_rejection": bool(
                result.get("financial_rejection", False)
            ),
        }

        if observability_logger is not None and observability_session_id is not None:
            _safe_observability_call(
                observability_logger.log_message,
                observability_session_id,
                "assistant",
                answer,
                blocked=diagnostics["financial_rejection"],
            )

        st.markdown(answer)
        render_assistant_diagnostics({"diagnostics": diagnostics})

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer,
        "diagnostics": diagnostics,
    })
