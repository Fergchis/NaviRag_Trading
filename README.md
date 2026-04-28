# NaviRag Trading

NaviRag Trading es una demo RAG educativa para **Iwakura Trading Academy** orientada a consultar PDFs de trading con trazabilidad documental.

El sistema permite cargar PDFs locales, extraer texto, generar chunks trazables, guardar embeddings en MongoDB Atlas Vector Search, recuperar fragmentos relevantes y generar respuestas educativas en Streamlit mostrando las fuentes utilizadas.

## Alcance y restriccion financiera

NaviRag Trading no es un sistema de trading real. No entrega senales, recomendaciones financieras, asesoria de inversion, predicciones, entradas, salidas, stop loss, take profit, precios objetivo, mercado en vivo ni backtesting real.

Las respuestas deben estar respaldadas por fragmentos recuperados desde los PDFs cargados. Si no existe contexto suficiente, la aplicacion debe indicarlo en vez de completar informacion con conocimiento externo.

## Configuracion local

Instala dependencias y crea el archivo de entorno local:

```bash
pip install -r requirements.txt
cp .env.example .env
```

En Windows PowerShell, el equivalente para copiar el archivo es:

```powershell
Copy-Item .env.example .env
```

Variables principales para GitHub Models:

```text
GITHUB_TOKEN=
GITHUB_EMBEDDING_MODEL=openai/text-embedding-3-small
GITHUB_CHAT_MODEL=openai/gpt-4o-mini
GITHUB_MODELS_EMBEDDINGS_ENDPOINT=https://models.github.ai/inference/embeddings
GITHUB_MODELS_CHAT_ENDPOINT=https://models.github.ai/inference/chat/completions
```

`GITHUB_TOKEN` es obligatorio para generar embeddings y respuestas con LLM. Los modelos y endpoints tienen valores por defecto en el codigo, pero pueden declararse en `.env` para dejar la configuracion explicita.

Las rutas documentales se resuelven desde constantes de `src/config.py`: `data/raw`, `data/processed` y `data/vectorstore`.

No subas `.env` al repositorio. El archivo contiene configuracion local y puede contener secretos.

## Prueba segura de MongoDB Atlas

MongoDB Atlas Vector Search es el vectorstore principal del pipeline RAG. Declara las variables MongoDB en `.env` sin subirlas al repositorio:

```text
MONGODB_CONNECTION_STRING=
MONGODB_DATABASE=navirag
MONGODB_COLLECTION=embeddings
MONGODB_VECTOR_INDEX=vector_index
```

Para verificar solo presencia de variables, sin mostrar secretos:

```bash
python -m src.utils.mongodb --check-env
```

Para probar conectividad con `ping`, solo si las variables ya existen localmente:

```bash
python -m src.utils.mongodb --ping
```

Para solicitar la creacion del indice Atlas Vector Search configurado:

```bash
python -m src.utils.mongodb --create-vector-index
```

Comando equivalente estilo Clase 1.4:

```bash
python create_vector_index.py
```

Para contar documentos en la coleccion configurada:

```bash
python -m src.utils.mongodb --count
```

Para migrar embeddings historicos desde JSON local a MongoDB Atlas, sin regenerarlos:

```bash
python scripts/migrate_json_embeddings_to_mongodb.py
```

## Flujo de procesamiento

1. Coloca los PDFs educativos en `data/raw/`.
2. Ejecuta la ingesta:

```bash
python -m src.ingesta.ingest
```

La ingesta extrae texto por archivo con `markitdown[pdf]` y guarda `data/processed/documents.json`.
Como MarkItDown entrega texto consolidado por documento en este flujo, la trazabilidad conserva `file`,
`path`, `section="document"` y `page=None` sin inventar numeros de pagina.

3. Genera chunks trazables:

```bash
python -m src.ingesta.chunking
```

El chunking guarda `data/processed/chunks.json` con `chunk_id`, archivo, pagina cuando exista,
seccion e indice de chunk dentro del documento procesado. Si `page=None`, la aplicacion y el prompt muestran
la seccion documental en vez de prometer una pagina. El chunking usa un split simple por caracteres con overlap,
siguiendo el estilo de Clase 1.4.

4. Genera embeddings con GitHub Models:

```bash
python -m src.utils.embeddings --limit 20
```

Este comando hace upsert incremental sobre la coleccion MongoDB existente. Despues de cambiar la ingesta o
el chunking, no mezcles embeddings antiguos con chunks nuevos: reindexa explicitamente desde cero.

Para reconstruir MongoDB completo desde los chunks locales actuales:

```bash
python -m src.utils.embeddings --rebuild-mongodb
```

`--rebuild-mongodb` borra primero todos los documentos de la coleccion configurada y luego genera embeddings
para todos los chunks. No lo combines con `--limit`.

Si un rebuild se interrumpe por rate limit u otro error despues de insertar parte de los chunks, continua sin
borrar MongoDB:

```bash
python -m src.utils.embeddings --resume-mongodb
```

`--resume-mongodb` lee los `chunk_id` ya presentes en MongoDB, omite esos chunks y genera embeddings solo para
los pendientes. No vuelvas a usar `--rebuild-mongodb` salvo que quieras borrar la coleccion configurada y empezar
desde cero.

Los embeddings se guardan en MongoDB Atlas Vector Search como unico vectorstore operativo.

Si existen embeddings historicos en JSON local, puedes cargarlos a MongoDB Atlas con:

```bash
python scripts/migrate_json_embeddings_to_mongodb.py
```

5. Ejecuta la interfaz Streamlit:

```bash
streamlit run app.py
```

Luego abre `http://localhost:8501`.

## Ejecucion con Docker

Construye la imagen:

```bash
docker build -t navirag-trading .
```

Ejecuta la app usando el archivo `.env` y montando `data/` para que los PDFs, documentos procesados y vectorstore permanezcan fuera de la imagen:

```bash
docker run --env-file .env -p 8501:8501 -v "${PWD}/data:/app/data" navirag-trading
```

En PowerShell:

```powershell
docker run --env-file .env -p 8501:8501 -v "${PWD}\data:/app/data" navirag-trading
```

## Datos locales no versionados

Los PDFs, chunks, embeddings, vectorstore y logs no se versionan. Permanecen como evidencia local privada y estan ignorados por `.gitignore`:

- `data/raw/`
- `data/processed/`
- `data/vectorstore/`
- `*.log`

Evidencia local no versionada usada para auditoria de la entrega:

- PDFs procesados: 5
- Documentos extraidos: 5
- Chunks generados: 338
- Embeddings en MongoDB: 338
- Modelo de embeddings: `openai/text-embedding-3-small`
- Vectorstore: MongoDB Atlas reindexado con los chunks simplificados actuales

## Estructura

```text
app.py             Interfaz Streamlit
prompts/           Plantillas de prompts
src/               Modulos de ingesta, chunking, embeddings, retrieval, generacion y safety
docs/              Arquitectura y decisiones tecnicas
eval/              Preguntas y resultados de evaluacion
data/raw/          PDFs locales ignorados por Git
data/processed/    JSON procesados ignorados por Git
data/vectorstore/  Artefactos JSON historicos ignorados por Git
```

## Evaluacion

La evaluacion documenta el comportamiento esperado de una demo academica: respuestas educativas con fuentes, rechazo de solicitudes financieras operativas y manejo explicito de consultas sin contexto suficiente. Ver `eval/evaluation_results.md`.

RAGAS queda preparado como evaluacion complementaria y manual, no como parte del runtime de Streamlit. El dataset esta en `eval/dataset.json` y el script en `eval/evaluate.py`.

Por defecto el script ejecuta solo una pregunta para evitar correr el dataset completo:

```bash
python eval/evaluate.py
```

La ejecucion real de RAGAS se probo parcialmente con una pregunta. El resultado preservado actualmente es `context_precision=1.0` para `RAGAS-01`; no se afirma evaluacion completa de las 8 preguntas ni de todas las metricas. `answer_relevancy` presento timeouts con GitHub Models y queda como limitacion documentada.

NaviRag usa GitHub Models; no se agrega `OPENAI_API_KEY` ni se cambia proveedor.
