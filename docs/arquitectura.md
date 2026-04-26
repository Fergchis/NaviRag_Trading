# Arquitectura de NaviRag Trading

NaviRag Trading es una demo RAG educativa para consultar PDFs locales de trading desde una interfaz Streamlit. El objetivo es explicar conceptos presentes en los documentos cargados, no operar mercados ni entregar asesoria financiera.

## Pipeline de indexacion

```text
PDFs locales en data/raw/
  -> src/ingest.py
  -> data/processed/documents.json
  -> src/chunking.py
  -> data/processed/chunks.json
  -> src/embeddings.py
  -> data/vectorstore/embeddings.json
```

## Pipeline de consulta

```text
pregunta del usuario
  -> src/safety.py
  -> embedding de pregunta
  -> src/retrieval.py
  -> src/prompts.py
  -> src/generator.py
  -> app.py / Streamlit con respuesta y fuentes visibles
```

## Componentes

- `src/ingest.py`: lee PDFs desde `data/raw/`, extrae texto por pagina y guarda metadatos basicos en `data/processed/documents.json`.
- `src/chunking.py`: segmenta el texto extraido en chunks trazables por archivo, pagina, `chunk_id` e indice dentro de la pagina.
- `src/embeddings.py`: genera embeddings para chunks usando GitHub Models y guarda registros locales en `data/vectorstore/embeddings.json`.
- `src/retrieval.py`: carga embeddings locales, embebe la pregunta del usuario y ordena chunks por similitud coseno.
- `src/prompts.py`: define el prompt educativo y las reglas para responder solo con contexto recuperado.
- `src/generator.py`: construye el contexto trazable, llama al endpoint de chat compatible con OpenAI y devuelve una respuesta controlada.
- `src/safety.py`: aplica un filtro simple por palabras clave para bloquear solicitudes obvias de asesoria financiera o senales operativas.
- `app.py`: expone el flujo en Streamlit, muestra la respuesta educativa, fragmentos recuperados y limitaciones.

## Persistencia local

El repositorio usa archivos JSON locales para mantener la demo simple y auditable:

- `data/processed/documents.json`: paginas extraidas.
- `data/processed/chunks.json`: chunks trazables.
- `data/vectorstore/embeddings.json`: embeddings y metadatos asociados.

Estos archivos se generan localmente y no se versionan.

## Seguridad funcional

La aplicacion bloquea consultas que pidan recomendaciones financieras, compra, venta, posiciones, apalancamiento, stop loss, take profit o predicciones. El prompt tambien exige que la generacion rechace decisiones operativas y use solo el contexto recuperado.

## Limitaciones

- La persistencia es JSON local, adecuada para demo academica, no para produccion.
- El vectorstore actual es parcial y debe declararse como tal.
- No hay cobertura completa garantizada del corpus.
- No se integran datos de mercado en vivo.
- No se implementa backtesting real.
- No hay conexion a brokers, exchanges ni ejecucion de ordenes.
- La capa de safety es una regla simple por keywords, no una moderacion robusta.
