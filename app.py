import uuid

import streamlit as st

from prompts.prompt import RAG_SYSTEM_PROMPT
from src.config import APP_NAME, ORGANIZATION
from src.generate.generate import RAGGenerator
from src.utils.safety import is_forbidden_question


st.set_page_config(page_title=APP_NAME, layout="wide")
st.title(APP_NAME)
st.caption(f"Demo educativa para {ORGANIZATION}")

with st.sidebar:
    st.header("Conversation")
    if st.button("New conversation"):
        st.session_state.history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

if "history" not in st.session_state:
    st.session_state.history = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "rag" not in st.session_state:
    st.session_state.rag = RAGGenerator(system_prompt=RAG_SYSTEM_PROMPT)

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
            if is_forbidden_question(query):
                answer = (
                    "No puedo entregar recomendaciones financieras, senales de "
                    "compra o venta ni instrucciones de inversion. Puedo explicar "
                    "conceptos de trading con fines educativos."
                )
                st.markdown(answer)
            else:
                with st.spinner("Thinking..."):
                    response = st.session_state.rag.generate(
                        query=query,
                        history=st.session_state.history[:-1],
                    )

                answer = response["answer"]
                st.markdown(answer)

                with st.expander("Sources"):
                    for source in response["sources"]:
                        st.write(
                            f"- {source.get('file')} | "
                            f"page: {source.get('page')} | "
                            f"section: {source.get('section')} | "
                            f"chunk: {source.get('page_chunk_index')} | "
                            f"chars: {source.get('character_count')}"
                        )

                with st.expander("Token usage"):
                    st.write(
                        f"Prompt: {response['prompt_tokens']} | "
                        f"Completion: {response['completion_tokens']} | "
                        f"Total: {response['total_tokens']}"
                    )

    st.session_state.history.append({"role": "assistant", "content": answer})
