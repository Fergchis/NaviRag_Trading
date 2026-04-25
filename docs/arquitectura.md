# Arquitectura de NaviRag Trading

NaviRag Trading es una demo RAG educativa para Iwakura Trading Academy. La aplicación se orienta a Streamlit y trabajará con PDFs cargados manualmente en `data/raw/`.

## Flujo previsto

```text
PDFs en data/raw/
  -> extracción de texto
  -> segmentación trazable
  -> embeddings
  -> vector store local
  -> consulta en Streamlit
  -> retrieval top-k
  -> prompt controlado
  -> respuesta educativa con fuentes
```

## Componentes

- `app.py`: interfaz Streamlit.
- `src/ingest.py`: futura extracción de texto desde PDFs.
- `src/chunking.py`: futura segmentación por documento, página, sección o unidad temática.
- `src/embeddings.py`: futura generación de embeddings.
- `src/retrieval.py`: futura recuperación de fragmentos relevantes.
- `src/prompts.py`: prompt base con restricciones educativas y de seguridad.
- `src/generator.py`: futura generación de respuestas basadas en contexto.
- `src/safety.py`: reglas simples para rechazar asesoría financiera y señales operativas.

## Estado actual

Esta etapa solo define la estructura y placeholders. No existe RAG funcional todavía.
