# NaviRag Trading

## Descripción

NaviRag Trading es una aplicación educativa para consultar documentos PDF sobre trading.

El proyecto usa RAG para recuperar contexto desde documentos locales y responder preguntas con apoyo de un LLM. La versión Ev2 agrega una capa mínima de agente funcional llamada `TradingAgent`.

El sistema no entrega recomendaciones financieras, señales de trading, instrucciones de compra o venta ni instrucciones de inversión.

## Arquitectura

Flujo de ingesta offline:

```text
PDFs locales -> Ingesta -> Embeddings -> MongoDB Atlas Vector Search
```

Flujo de consulta runtime:

```mermaid
flowchart TD
    U[Usuario] --> S[Streamlit]
    S --> A[TradingAgent]
    A --> G[LangGraph StateGraph]
    G --> M[load_memory]
    M --> F[check_financial_safety]
    F -->|bloquea| B[blocked_response]
    F -->|permite| P[agent LLM con bind_tools]
    P -->|tool_calls| Q[generate_query con LLM]
    Q --> R[ToolNode: rag_search]
    R --> P
    B --> SV[save_memory]
    P -->|respuesta final| SV
    SV --> O[Respuesta educativa con fuentes]
```

La tool declarativa `rag_search` consulta MongoDB Atlas Vector Search. El nodo `agent` usa GitHub Models mediante `ChatOpenAI.bind_tools`, decide la llamada y recibe el resultado desde `ToolNode` antes de responder.

El sistema usa:

- Streamlit para la interfaz.
- MongoDB Atlas Vector Search para búsqueda semántica.
- GitHub Models para embeddings y generación de respuestas.
- LangChain para declarar herramientas del agente.
- LangGraph para conectar nodos y rutas condicionales.
- RAGAS para una evaluación básica.

El cliente LLM propio (`GitHubModelsLLM`) se mantiene para el RAG tradicional. El grafo usa un cliente `ChatOpenAI` configurado con GitHub Models para soportar `bind_tools` y `tool_calls`.

## Agente Ev2

`TradingAgent` envuelve el RAG existente con una capa simple de agente basada en LangGraph.

El agente:

- ejecuta herramientas explícitas;
- mantiene memoria de corto y largo plazo;
- usa un LLM con tools enlazadas para decidir la búsqueda;
- ejecuta las tools mediante `ToolNode`;
- enruta según los `tool_calls` producidos por el modelo;
- reformula la consulta mediante un prompt y un LLM;
- conserva el enfoque educativo del sistema.

### Herramientas

| Tool | Función |
|---|---|
| `rag_search` | Recupera contexto y fuentes desde MongoDB Atlas Vector Search. |

Safety y memoria permanecen como nodos explícitos del grafo; no se presentan como tools del LLM.

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

El flujo ya no queda como una lista rígida de pasos. El agente usa `bind_tools`, `ToolNode` y un `StateGraph` con nodos pequeños:

- `load_memory`;
- `check_financial_safety`;
- `blocked_response`;
- `agent`;
- `generate_query`;
- `tools`;
- `save_memory`.

Las rutas condicionales permiten:

- bloquear sin consultar el RAG;
- permitir que el LLM seleccione `rag_search`;
- reformular la consulta antes de recuperar contexto;
- responder falta de contexto si no hay chunks útiles;
- guardar memoria al final del flujo.

Rutas de decisión:

- `blocked`: la pregunta pide recomendación financiera, señal o instrucción de inversión.
- `insufficient_context`: no hay chunks recuperados o no tienen texto útil.
- `rag_answer`: se genera una respuesta educativa con contexto recuperado.

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
│   │   ├── graph.py        # Grafo con bind_tools y ToolNode
│   │   ├── memory.py       # Memoria short-term y long-term
│   │   └── tools.py        # Tool rag_search declarada con LangChain
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
│   ├── evaluate.py         # Evaluación con RAGAS
│   ├── casos_ev2.json      # Casos ejecutables del agente
│   └── run_casos_ev2.py    # Validador de rutas EV2
└── data/
    ├── raw/                # PDFs locales
    └── memory/             # Memoria local ignorada por Git
```

## Setup

Para iniciar el proyecto de manera correcta se recomienda leer el archivo llamado "COMO_EJECUTAR.md".

Ejecución local con Streamlit:

```powershell
python -m streamlit run app.py
```

Ejecución con Docker:

```powershell
docker build -t navirag-trading .
docker run --rm -p 8501:8501 --env-file .env navirag-trading
```

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

El archivo `eval/casos_ev2.json` contiene casos exitosos y defectuosos ejecutables:

```bash
python eval/run_casos_ev2.py
```

## Corrección V2

La corrección responde a la retroalimentación docente con cambios acotados:

- reemplaza el planner rígido por un agente LLM con `bind_tools`;
- usa `ToolNode` y routing basado en `tool_calls`;
- reformula la query con un prompt y un LLM;
- ejecuta casos exitosos y defectuosos desde consola;
- mantiene Streamlit, MongoDB Atlas Vector Search y GitHub Models.

## Limitaciones

- No es un sistema de trading operativo.
- No ejecuta órdenes.
- No entrega señales de compra o venta.
- No usa datos de mercado en tiempo real.
- La memoria long-term es un JSON local simple.
- La seguridad financiera usa reglas básicas.
- El sistema depende de MongoDB Atlas y GitHub Models.
