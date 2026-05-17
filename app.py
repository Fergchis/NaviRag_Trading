import uuid

import streamlit as st

from src.agent import TradingAgent
from src.config import APP_NAME, ORGANIZATION


st.set_page_config(page_title=APP_NAME, layout="wide")
st.title(APP_NAME)
st.caption(f"Demo educativa para {ORGANIZATION}")

with st.sidebar:
    st.header("Conversación")
    if st.button("Nueva conversación"):
        st.session_state.history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

if "history" not in st.session_state:
    st.session_state.history = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "agent" not in st.session_state:
    st.session_state.agent = TradingAgent()

chat_window = st.container(height=550)
with chat_window:
    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if query := st.chat_input("Pregunta sobre los PDFs de trading..."):
    st.session_state.history.append({"role": "user", "content": query})

    with chat_window:
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Procesando..."):
                result = st.session_state.agent.run(
                    query=query,
                    history=st.session_state.history[:-1],
                    session_id=st.session_state.session_id,
                )

            answer = result["answer"]
            st.markdown(answer)

            with st.expander("Fuentes"):
                for source in result["sources"]:
                    source_details = [
                        f"- {source.get('file')}",
                        f"section: {source.get('section')}",
                        f"chunk: {source.get('page_chunk_index')}",
                        f"chars: {source.get('character_count')}",
                    ]
                    if source.get("page") is not None:
                        source_details.insert(1, f"page: {source.get('page')}")
                    st.write(" | ".join(source_details))

            with st.expander("Uso de tokens"):
                st.write(
                    f"Prompt: {result['prompt_tokens']} | "
                    f"Completion: {result['completion_tokens']} | "
                    f"Total: {result['total_tokens']}"
                )

            with st.expander("Plan ejecutado"):
                st.write(result["plan"])

            with st.expander("Decisión del agente"):
                st.write(result["decision"])
                st.write(result["memory"])

    st.session_state.history.append({"role": "assistant", "content": answer})
