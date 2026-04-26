"""Streamlit entry point for NaviRag Trading."""

import streamlit as st

from src.config import APP_NAME, ORGANIZATION
from src.generator import generate_answer
from src.retrieval import retrieve
from src.safety import is_forbidden_question


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
            results = retrieve(question=question, top_k=top_k)
        except FileNotFoundError as error:
            st.error(str(error))
            st.info("Genera embeddings antes de consultar desde la app.")
        except RuntimeError as error:
            _ = error
            st.error(
                "No se pudo ejecutar retrieval. Revisa la configuracion de "
                "GitHub Models, cuota, permisos o conectividad."
            )
        except Exception as error:
            _ = error
            st.error("Ocurrio un error inesperado durante retrieval.")
        else:
            st.subheader("Pregunta")
            st.write(question)

            st.subheader("Respuesta educativa")
            if not results:
                st.warning("No se recuperaron fragmentos para esta consulta.")

            try:
                answer = generate_answer(question=question, chunks=results)
            except RuntimeError as error:
                _ = error
                st.error(
                    "No se pudo generar la respuesta con LLM. Revisa la "
                    "configuracion del proveedor de chat."
                )
            except Exception as error:
                _ = error
                st.error("Ocurrio un error inesperado durante la generacion.")
            else:
                st.write(answer)

            st.subheader("Fragmentos recuperados")
            if not results:
                st.warning("No se recuperaron fragmentos para esta consulta.")

            for index, result in enumerate(results, start=1):
                title = (
                    f"{index}. {result.get('file')} | "
                    f"pagina {result.get('page')} | "
                    f"score {result.get('score', 0):.4f}"
                )
                with st.expander(title, expanded=index == 1):
                    st.caption(
                        f"chunk_id: {result.get('chunk_id')} | "
                        f"page_chunk_index: {result.get('page_chunk_index')}"
                    )
                    st.write(result.get("text", ""))

            st.subheader("Limitaciones")
            st.write(
                "La respuesta se genera solo desde los fragmentos recuperados. "
                "No reemplaza la revision del material fuente ni constituye "
                "asesoria financiera."
            )
