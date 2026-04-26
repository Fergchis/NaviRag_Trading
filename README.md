# NaviRag Trading

Demo RAG educativa para **Iwakura Trading Academy** orientada a consultar PDFs de trading con trazabilidad documental.

El proyecto implementa una canalizacion RAG simple: ingesta de PDFs, chunking trazable, embeddings con GitHub Models, retrieval local por similitud coseno y generacion educativa con LLM en Streamlit mostrando fuentes. No implementa senales de trading, recomendaciones financieras, asesoria de inversion, datos de mercado en vivo ni backtesting real.

## Alcance actual

- Ingesta PDF desde `data/raw/`.
- Chunking trazable por archivo, pagina y chunk.
- Embeddings con GitHub Models.
- Retrieval local por similitud coseno.
- Generacion educativa con LLM basada solo en fragmentos recuperados.
- Aplicacion Streamlit con respuesta y fuentes.
- Documentacion tecnica minima.
- Preguntas iniciales de evaluacion.

## Ejecucion local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Ingesta simple de PDFs

Coloca los PDFs educativos de trading en `data/raw/`. Esa carpeta es solo para el corpus documental de NaviRag Trading.

Luego ejecuta:

```bash
python -m src.ingest
```

La salida procesada se guarda en `data/processed/documents.json`. Esta fase extrae texto y metadatos basicos por archivo y pagina.

Para generar chunks trazables desde el texto procesado:

```bash
python -m src.chunking
```

La salida se guarda en `data/processed/chunks.json`.

Para generar embeddings de prueba con GitHub Models:

```bash
python -m src.embeddings --limit 20
```

Para continuar una generacion interrumpida sin reprocesar chunks existentes:

```bash
python -m src.embeddings --resume --limit 50
```

La salida se guarda en `data/vectorstore/embeddings.json`. Esta fase usa `GITHUB_TOKEN`, `GITHUB_MODELS_ENDPOINT` y `EMBEDDING_MODEL` desde `.env`.

Para probar retrieval local por similitud coseno:

```bash
python -m src.retrieval "que dice el material sobre gestion de riesgo" --top-k 3
```

La app de Streamlit usa esos fragmentos recuperados para generar una respuesta educativa con LLM. Configura en `.env` `GITHUB_TOKEN`, `GITHUB_CHAT_ENDPOINT` y `CHAT_MODEL`; la respuesta debe basarse solo en los chunks mostrados como fuentes debajo de la respuesta.

## Ejecucion con Docker

```bash
docker build -t navirag-trading .
docker run -p 8501:8501 navirag-trading
```

Luego abre `http://localhost:8501`.

## Estructura

```text
data/raw/          PDFs cargados manualmente
data/processed/    documentos y chunks procesados
data/vectorstore/  embeddings generados y vector store local
src/               modulos de la aplicacion
eval/              preguntas y resultados de evaluacion
docs/              diseno, arquitectura y decisiones tecnicas
```

## Restricciones

NaviRag Trading tiene fines academicos. El sistema debe responder solo con informacion respaldada por documentos cargados y rechazar solicitudes de compra, venta, prediccion, entradas, salidas, stop loss, take profit o asesoria financiera personalizada.
