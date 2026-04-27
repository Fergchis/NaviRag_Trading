"""Streamlit entry point for NaviRag Trading."""

import streamlit as st

from src.config import APP_NAME, ORGANIZATION
from src.generate.generate import RAGGenerator
from src.utils.safety import is_forbidden_question


def format_source_title(index: int, result: dict) -> str:
    """Build a source title without inventing page numbers."""
    if result.get("page") is not None:
        location = f"pagina {result.get('page')}"
    elif result.get("section"):
        location = f"seccion {result.get('section')}"
    else:
        location = "pagina no disponible"

    return (
        f"{index}. {result.get('file')} | "
        f"{location} | "
        f"score {result.get('score', 0):.4f}"
    )


st.set_page_config(page_title=APP_NAME, layout="centered")

st.title(APP_NAME)
st.caption(f"Demo educativa para {ORGANIZATION}")

st.info(
    "NaviRag Trading recupera fragmentos desde documentos cargados con fines "
    "educativos. No entrega senales de trading, recomendaciones financieras "
    "ni asesoria de inversion."
)

top_k = st.slider("Cantidad de fragmentos a recuperar", min_value=1, max_value=5, value=3)

question = st.text_area(
    "Pregunta educativa sobre los documentos cargados",
    placeholder="Ejemplo: Que dice el material sobre gestion de riesgo?",
)

if st.button("Consultar", type="primary"):
    if not question.strip():
        st.warning("Ingresa una pregunta para continuar.")
    elif is_forbidden_question(question):
        st.error(
            "No puedo entregar senales de compra o venta, recomendaciones "
            "financieras ni asesoria de inversion. NaviRag Trading tiene un "
            "enfoque educativo y solo puede explicar conceptos presentes en "
            "los documentos cargados."
        )
    else:
        try:
            response = RAGGenerator().generate(query=question, history=[], top_k=top_k)
            results = response["sources"]
        except FileNotFoundError as error:
            st.error(str(error))
            st.info("Genera embeddings antes de consultar desde la app.")
        except RuntimeError as error:
            _ = error
            st.error(
                "No se pudo ejecutar RAG. Revisa la configuracion de "
                "GitHub Models, MongoDB, cuota, permisos o conectividad."
            )
        except Exception as error:
            _ = error
            st.error("Ocurrio un error inesperado durante RAG.")
        else:
            st.subheader("Pregunta")
            st.write(question)

            st.subheader("Respuesta educativa")
            if not results:
                st.warning("No se recuperaron fragmentos para esta consulta.")

            st.write(response["answer"])

            st.subheader("Fragmentos recuperados")
            if not results:
                st.warning("No se recuperaron fragmentos para esta consulta.")

            for index, result in enumerate(results, start=1):
                title = format_source_title(index, result)
                with st.expander(title, expanded=index == 1):
                    st.caption(
                        f"chunk_id: {result.get('chunk_id')} | "
                        f"section: {result.get('section')} | "
                        f"page_chunk_index: {result.get('page_chunk_index')}"
                    )
                    st.write(result.get("text", ""))

            st.subheader("Limitaciones")
            st.write(
                "La respuesta se genera solo desde los fragmentos recuperados. "
                "No reemplaza la revision del material fuente ni constituye "
                "asesoria financiera."
            )
