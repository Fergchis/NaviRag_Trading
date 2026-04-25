"""Streamlit entry point for NaviRag Trading."""

import streamlit as st

from src.config import APP_NAME, ORGANIZATION
from src.generator import generate_placeholder_answer
from src.retrieval import retrieve_placeholder_context
from src.safety import is_forbidden_question


st.set_page_config(page_title=APP_NAME, layout="centered")

st.title(APP_NAME)
st.caption(f"Demo educativa para {ORGANIZATION}")

st.info(
    "Esta versión inicial solo prepara la estructura del proyecto. "
    "La ingesta de PDFs, embeddings, vector store y generación RAG real "
    "se implementarán en etapas posteriores."
)

question = st.text_area(
    "Pregunta educativa sobre los documentos cargados",
    placeholder="Ejemplo: ¿Qué dice el material sobre gestión de riesgo?",
)

if st.button("Consultar", type="primary"):
    if not question.strip():
        st.warning("Ingresa una pregunta para continuar.")
    elif is_forbidden_question(question):
        st.error(
            "No puedo entregar señales de compra o venta, recomendaciones "
            "financieras ni asesoría de inversión. NaviRag Trading tiene un "
            "enfoque educativo y solo puede explicar conceptos presentes en "
            "los documentos cargados."
        )
    else:
        context = retrieve_placeholder_context(question)
        answer = generate_placeholder_answer(question, context)

        st.subheader("Respuesta")
        st.write(answer)

        st.subheader("Fuentes o fragmentos recuperados")
        st.write(
            "Aún no hay fragmentos reales recuperados. Esta sección queda "
            "reservada para mostrar documento, página y fragmento cuando se "
            "implemente el flujo RAG."
        )

        st.subheader("Limitaciones")
        st.write(
            "La respuesta actual es un placeholder. No usa PDFs, embeddings, "
            "vector store ni un modelo generativo."
        )
