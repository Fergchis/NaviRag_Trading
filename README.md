# NaviRag Trading

## Descripción

NaviRag Trading es una aplicación educativa para consultar documentos PDF sobre trading.

El proyecto usa RAG para recuperar contexto desde documentos locales y responder preguntas con apoyo de un LLM. La versión Ev2 agrega una capa mínima de agente funcional llamada `TradingAgent`.

El sistema no entrega recomendaciones financieras, señales de trading, instrucciones de compra o venta ni instrucciones de inversión.

## Arquitectura

Flujo de ingesta:

```text
PDFs locales
  -> Ingesta
  -> Embeddings
  -> MongoDB Atlas Vector Search
```

Flujo de consulta:

```text
Usuario
  -> Streamlit
  -> TradingAgent
  -> Tools
  -> Respuesta educativa con fuentes
```

Desde las tools:

- `retrieve_context_tool` consulta MongoDB Atlas Vector Search.
- `write_answer_tool` usa GitHub Models.
- Las tools de memoria usan `data/memory/`.

El sistema usa:

- Streamlit para la interfaz.
- MongoDB Atlas Vector Search para búsqueda semántica.
- GitHub Models para embeddings y generación de respuestas.
- LangChain para declarar herramientas del agente.
- RAGAS para una evaluación básica.

El cliente LLM propio (`GitHubModelsLLM`) se mantiene. LangChain se usa para definir tools, no para reemplazar el cliente de GitHub Models.

## Agente Ev2

`TradingAgent` envuelve el RAG existente con una capa simple de agente.

El agente:

- ejecuta herramientas explícitas;
- mantiene memoria de corto y largo plazo;
- usa planificación simple;
- toma decisiones según seguridad, contexto y errores externos;
- conserva el enfoque educativo del sistema.

### Herramientas

| Tool | Función |
|---|---|
| `load_memory_tool` | Carga memoria local de la sesión. |
| `safety_check_tool` | Valida si la pregunta pide recomendaciones financieras o señales. |
| `retrieve_context_tool` | Recupera chunks desde MongoDB Atlas Vector Search. |
| `write_answer_tool` | Genera una respuesta usando chunks ya recuperados. |
| `save_memory_tool` | Guarda datos mínimos de continuidad de sesión. |

### Memoria

- Short-term memory: usa el historial reciente de Streamlit.
- Long-term memory: usa JSON local en `data/memory/session_memory.json`.
- `session_memory.json` se ignora por Git.
- La carpeta `data/memory/` se conserva con `.gitkeep`.

La memoria local guarda datos mínimos:

- `session_id`;
- últimas preguntas no bloqueadas;
- ruta de decisión;
- timestamp;
- contador de interacciones.

### Planificación y decisiones

El planner no usa LLM. Ejecuta un flujo fijo y fácil de revisar:

1. cargar memoria;
2. validar seguridad;
3. recuperar contexto;
4. generar respuesta;
5. guardar memoria.

Rutas de decisión:

- `blocked`: la pregunta pide recomendación financiera, señal o instrucción de inversión.
- `insufficient_context`: no hay chunks recuperados o no tienen texto útil.
- `rag_answer`: se genera una respuesta educativa con contexto recuperado.
- `retrieval_error`: falla la recuperación desde la base de documentos.
- `generation_error`: falla la generación del LLM.

## Estructura del proyecto

```text
├── app.py                  # Aplicación principal en Streamlit
├── create_vector_index.py  # Creación del índice vectorial
├── requirements.txt        # Dependencias del proyecto
├── prompts/
│   └── prompt.py           # Prompt del sistema RAG
├── src/
│   ├── agent/
│   │   ├── agent.py        # TradingAgent
│   │   ├── memory.py       # Memoria short-term y long-term
│   │   ├── planner.py      # Planner simple
│   │   └── tools.py        # Tools declaradas con LangChain
│   ├── config.py           # Configuración general
│   ├── ingesta/
│   │   └── ingest.py       # Ingesta de PDFs
│   ├── retrieval/
│   │   └── retrieval.py    # Recuperación semántica
│   ├── generate/
│   │   └── generate.py     # Generación RAG
│   └── utils/
│       ├── embeddings.py   # Embeddings con GitHub Models
│       ├── llm.py          # Cliente LLM propio
│       ├── mongodb.py      # Conexión a MongoDB
│       └── safety.py       # Seguridad financiera básica
├── eval/
│   ├── dataset.json        # Dataset de evaluación
│   └── evaluate.py         # Evaluación con RAGAS
└── data/
    ├── raw/                # PDFs locales
    └── memory/             # Memoria local ignorada por Git
```

## Setup

### 1. Variables de entorno

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

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Crear índice vectorial

```bash
python create_vector_index.py
```

El índice usa la configuración definida en las variables de entorno.

## Ingesta de PDFs

Agregar los archivos PDF en:

```text
data/raw/
```

Luego ejecutar:

```bash
python -c "from src.ingesta.ingest import PDFIngester; PDFIngester().ingest_directory('data/raw')"
```

Este proceso lee los PDFs, genera embeddings y guarda los chunks en MongoDB Atlas.

## Ejecutar la aplicación

```bash
streamlit run app.py
```

Abrir la aplicación en el navegador y realizar preguntas sobre los documentos cargados.

## Ejecutar en otro PC

Clonar el repositorio no es suficiente para ejecutar todo el proyecto. NaviRag Trading depende de servicios externos, variables locales, MongoDB Atlas y documentos previamente ingeridos.

### 1. Clonar el repositorio

```powershell
git clone https://github.com/Fergchis/NaviRag_Trading.git
cd NaviRag_Trading
git checkout version-2
```

### 2. Crear entorno virtual e instalar dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crear un archivo `.env` local usando `.env.example` como referencia.

Ejemplo sin valores reales:

```env
GITHUB_TOKEN=...
GITHUB_EMBEDDING_MODEL=openai/text-embedding-3-small
GITHUB_CHAT_MODEL=openai/gpt-4o-mini
GITHUB_MODELS_EMBEDDINGS_ENDPOINT=https://models.github.ai/inference/embeddings

MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE=navirag
MONGODB_COLLECTION=embeddings
MONGODB_VECTOR_INDEX=vector_index
```

Además, en MongoDB Atlas la IP pública del nuevo PC debe estar permitida en **Network Access**.

### 4. Elegir fuente documental

Existen dos formas de usar la base documental.

#### Opción A: usar MongoDB Atlas ya cargado

Esta opción sirve si la base ya tiene documentos ingeridos.

Requisitos:

- colección con chunks existentes;
- índice vectorial creado;
- credenciales correctas en `.env`;
- IP permitida en MongoDB Atlas.

Ejecutar la aplicación:

```powershell
python -m streamlit run app.py
```

#### Opción B: reconstruir la base documental

Esta opción sirve si se quiere cargar nuevamente los PDFs desde el PC local.

Requisitos:

- PDFs dentro de `data/raw/`;
- token válido para GitHub Models;
- MongoDB Atlas configurado;
- variables de entorno completas.

Crear índice, ejecutar ingesta y levantar Streamlit:

```powershell
python create_vector_index.py

python -c "from src.ingesta.ingest import PDFIngester; PDFIngester().ingest_directory('data/raw')"

python -m streamlit run app.py
```

El repositorio no incluye `.env`, PDFs pesados ni memoria local de sesión. Estos archivos se configuran localmente.

## Evaluación

El proyecto incluye una evaluación básica con RAGAS usando `eval/dataset.json`.

```bash
python eval/evaluate.py
```

También se puede validar manualmente el agente con casos como:

- pregunta educativa con contexto;
- pregunta de seguimiento;
- pregunta sin contexto suficiente;
- pregunta bloqueada por seguridad financiera.

## Limitaciones

- No es un sistema de trading operativo.
- No ejecuta órdenes.
- No entrega señales de compra o venta.
- No usa datos de mercado en tiempo real.
- La memoria long-term es un JSON local simple.
- La seguridad financiera usa reglas básicas.
- El sistema depende de MongoDB Atlas y GitHub Models.
