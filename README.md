# NaviRag Trading

RAG educativo desarrollado con Python y Streamlit para consultar PDFs locales sobre trading.

El proyecto permite cargar documentos PDF, guardar sus embeddings en MongoDB Atlas y responder preguntas usando GitHub Models.

## Architecture

```text
PDFs locales → Ingesta → MongoDB Atlas → Retrieval → LLM → Respuesta
```

El sistema usa:

- Streamlit para la interfaz.
- MongoDB Atlas Vector Search para búsqueda por embeddings.
- GitHub Models para embeddings y generación de respuestas.
- RAGAS para una evaluación básica.

Nota: el sistema incluye una regla simple de seguridad financiera para evitar recomendaciones de compra, venta, inversión o señales de trading.

## Project Structure

```text
├── app.py                  # Aplicación principal en Streamlit
├── create_vector_index.py  # Creación del índice vectorial
├── requirements.txt        # Dependencias del proyecto
├── prompts/
│   └── prompt.py           # Prompt del sistema
├── src/
│   ├── config.py           # Configuración general
│   ├── ingesta/
│   │   └── ingest.py       # Ingesta de PDFs con PDFIngester
│   ├── retrieval/
│   │   └── retrieval.py    # Recuperación de documentos
│   ├── generate/
│   │   └── generate.py     # Generación de respuestas
│   └── utils/
│       ├── embeddings.py   # Embeddings con GitHub Models
│       ├── llm.py          # Cliente LLM
│       ├── mongodb.py      # Conexión a MongoDB
│       └── safety.py       # Seguridad financiera básica
├── eval/
│   ├── dataset.json        # Dataset de evaluación
│   └── evaluate.py         # Evaluación con RAGAS
└── data/
    └── raw/                # PDFs locales
```

## Setup

### 1. Environment variables

Crear un archivo `.env` en la raíz del proyecto:

```env
APP_ENV=local

GITHUB_TOKEN=your_github_token
GITHUB_EMBEDDING_MODEL=openai/text-embedding-3-small
GITHUB_CHAT_MODEL=openai/gpt-4o-mini
GITHUB_MODELS_EMBEDDINGS_ENDPOINT=https://models.github.ai/inference/embeddings

MONGODB_CONNECTION_STRING=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DATABASE=navirag
MONGODB_COLLECTION=embeddings
MONGODB_VECTOR_INDEX=vector_index
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. MongoDB Atlas — Vector Search Index

Crear el índice vectorial en MongoDB Atlas:

```bash
python create_vector_index.py
```

El índice usa la configuración definida en las variables de entorno.

### 4. Ingest PDFs

Agregar los archivos PDF en la carpeta:

```text
data/raw/
```

Luego ejecutar la ingesta:

```bash
python -c "from src.ingesta.ingest import PDFIngester; PDFIngester().ingest_directory('data/raw')"
```

Este proceso lee los PDFs, genera embeddings y guarda la información en MongoDB Atlas.

### 5. Run Streamlit

```bash
streamlit run app.py
```

Abrir la aplicación en el navegador y realizar preguntas sobre los documentos cargados.

### 6. Evaluation

El proyecto incluye una evaluación básica con RAGAS usando `eval/dataset.json`.

```bash
python eval/evaluate.py
```

## What is it missing?

1. Agregar más PDFs para probar el sistema.
2. Mejorar el dataset de evaluación.
3. Probar más preguntas relacionadas con trading.
4. Revisar más casos de seguridad financiera.
5. Mejorar la presentación de fuentes en la interfaz.
