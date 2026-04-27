# Arquitectura de NaviRag Trading

NaviRag Trading es una demo RAG educativa para consultar PDFs locales de trading desde una interfaz Streamlit. El objetivo es explicar conceptos presentes en los documentos cargados, no operar mercados ni entregar asesoria financiera.

## Pipeline de indexacion

```text
PDFs locales en data/raw/
  -> src/ingesta/ingest.py
  -> data/processed/documents.json
  -> src/ingesta/chunking.py
  -> data/processed/chunks.json
  -> src/utils/embeddings.py
  -> MongoDB Atlas Vector Search
```

## Pipeline de consulta

```text
pregunta del usuario
  -> src/utils/safety.py
  -> embedding de pregunta
  -> src/retrieval/retrieval.py con MongoDB Atlas Vector Search
  -> prompts/prompt.py
  -> src/generate/generate.py
  -> app.py / Streamlit con respuesta y fuentes visibles
```

## Componentes

- `src/ingesta/ingest.py`: lee PDFs desde `data/raw/`, extrae texto con `markitdown[pdf]` y guarda metadatos basicos en `data/processed/documents.json`. En este flujo MarkItDown entrega texto consolidado por documento, por lo que `page` queda en `None` y `section` queda como `document`.
- `src/ingesta/chunking.py`: segmenta el texto extraido en chunks trazables por archivo, ruta, pagina cuando exista, seccion, `chunk_id` e indice dentro del documento procesado. Fusiona bloques pequenos de MarkItDown para evitar chunks demasiado fragmentados.
- `src/utils/embeddings.py`: genera embeddings para chunks usando GitHub Models y conserva metadata trazable como archivo, pagina cuando exista, seccion e indice de chunk.
- `src/utils/mongodb.py`: centraliza configuracion, ping, upsert de embeddings e indice Atlas Vector Search. Guarda `section` dentro de `metadata` para futuras regeneraciones sin cambiar el campo vectorial ni el identificador `chunk_id`.
- `create_vector_index.py`: comando raiz para solicitar el indice vectorial de MongoDB Atlas.
- `scripts/migrate_json_embeddings_to_mongodb.py`: migra embeddings historicos desde JSON local a MongoDB Atlas sin regenerarlos.
- `src/retrieval/retrieval.py`: embebe la pregunta del usuario y consulta MongoDB Atlas Vector Search.
- `prompts/prompt.py`: define el prompt educativo y las reglas para responder solo con contexto recuperado.
- `src/generate/generate.py`: construye el contexto trazable, llama a GitHub Models y devuelve una respuesta controlada.
- `src/utils/safety.py`: aplica un filtro simple por palabras clave para bloquear solicitudes obvias de asesoria financiera o senales operativas.
- `app.py`: expone el flujo en Streamlit, muestra la respuesta educativa, fragmentos recuperados y limitaciones.

## Persistencia

El vectorstore operativo es MongoDB Atlas Vector Search. El repositorio puede conservar archivos JSON locales como evidencia historica ignorada por Git:

- `data/processed/documents.json`: documentos extraidos con metadata trazable.
- `data/processed/chunks.json`: chunks trazables.
- `data/vectorstore/embeddings.json`: artefacto historico de embeddings y metadatos asociados.

Estos archivos se generan localmente y no se versionan.

## Seguridad funcional

La aplicacion bloquea consultas que pidan recomendaciones financieras, compra, venta, posiciones, apalancamiento, stop loss, take profit o predicciones. El prompt tambien exige que la generacion rechace decisiones operativas y use solo el contexto recuperado.

## Limitaciones

- La persistencia vectorial principal depende de MongoDB Atlas.
- El vectorstore actual es parcial y debe declararse como tal.
- No hay cobertura completa garantizada del corpus.
- No se integran datos de mercado en vivo.
- No se implementa backtesting real.
- No hay conexion a brokers, exchanges ni ejecucion de ordenes.
- La capa de safety es una regla simple por keywords, no una moderacion robusta.
