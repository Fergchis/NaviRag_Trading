# NaviRag Trading

RAG educativo para consultar PDFs locales de trading usando GitHub Models, MongoDB Atlas Vector Search y Streamlit.

NaviRag Trading responde solo con el contexto recuperado desde los documentos. No entrega recomendaciones financieras, senales de compra o venta ni instrucciones de inversion.

## Architecture

```text
PDFs locales -> Ingesta -> MongoDB Atlas -> Retrieval -> GitHub Models -> Respuesta
```

| Component | Technology |
|-----------|------------|
| Embeddings | GitHub Models `openai/text-embedding-3-small` |
| Vector DB | MongoDB Atlas Vector Search |
| LLM | GitHub Models `openai/gpt-4o-mini` |
| UI | Streamlit |
| Evaluation | RAGAS |

## Project Structure

```text
app.py                  # Streamlit app
create_vector_index.py  # MongoDB Atlas Vector Search index
Dockerfile
requirements.txt
prompts/
src/
  ingesta/              # PDF ingestion
  retrieval/            # Vector search
  generate/             # RAG generation
  utils/                # GitHub Models, MongoDB and safety helpers
eval/
  dataset.json
  evaluate.py
data/
  raw/                  # Local PDFs ignored by Git
```

## Setup

Create a `.env` file:

```env
GITHUB_TOKEN=
GITHUB_EMBEDDING_MODEL=openai/text-embedding-3-small
GITHUB_CHAT_MODEL=openai/gpt-4o-mini

MONGODB_CONNECTION_STRING=
MONGODB_DATABASE=navirag
MONGODB_COLLECTION=embeddings
MONGODB_VECTOR_INDEX=vector_index
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## MongoDB Atlas Index

Create the vector search index:

```bash
python create_vector_index.py
```

The index uses:

```json
{
  "fields": [{
    "type": "vector",
    "path": "embedding",
    "numDimensions": 1536,
    "similarity": "cosine"
  }]
}
```

## Ingest Local PDFs

Place the valid PDFs in `data/raw/` and run a small ingestion call:

```bash
python -c "from src.ingesta.ingest import PDFIngester; PDFIngester().ingest_directory('data/raw')"
```

`scan_pdfs` only reads PDFs directly inside `data/raw/`, so excluded files in nested folders are not processed.

## Run Streamlit

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

## Evaluation

RAGAS evaluation is optional:

```bash
python eval/evaluate.py
```
