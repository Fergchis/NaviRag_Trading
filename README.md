# NaviRAG Trading

Agente educativo para consultar documentos PDF sobre trading. Usa LangGraph para coordinar agentes especializados, MongoDB Atlas Vector Search para recuperar contexto y GitHub Models para embeddings y respuestas.

El sistema no ejecuta operaciones ni entrega recomendaciones financieras directas, señales de compra o venta o instrucciones de inversión.

## Arquitectura

```text
Usuario
  └── Streamlit
        └── Supervisor
              ├── rag_agent     → recuperación documental
              ├── memory_agent  → memoria long-term
              └── answer_agent  → respuesta final
```

El supervisor selecciona rutas directas o recorridos compuestos. El agente RAG contiene un subgrafo con reformulación de consulta, `ToolNode` y `rag_search`. La memoria conversacional usa `MemorySaver`; la memoria entre conversaciones usa `InMemoryStore` y la tool explícita `save_memory`.

La descripción completa de nodos, edges, rutas, tools y evidencia EV2 está en [docs/flujo_langgraph_ev2.md](docs/flujo_langgraph_ev2.md).

## Requisitos

- Python 3.11 o Docker.
- Token con acceso a GitHub Models.
- MongoDB Atlas con la colección documental y el índice vectorial configurados.
- Dependencias declaradas en `requirements.txt`.

## Variables de entorno

Crear `.env` a partir de `.env.example`. Variables principales:

```text
GITHUB_TOKEN=
GITHUB_CHAT_MODEL=openai/gpt-4o-mini
GITHUB_EMBEDDING_MODEL=openai/text-embedding-3-small
GITHUB_MODELS_CHAT_ENDPOINT=https://models.github.ai/inference/chat/completions
GITHUB_MODELS_EMBEDDINGS_ENDPOINT=https://models.github.ai/inference/embeddings

MONGODB_CONNECTION_STRING=
MONGODB_DATABASE=navirag
MONGODB_COLLECTION=embeddings
MONGODB_VECTOR_INDEX=vector_index
```

## Ejecución

Ejecución local, después de preparar el entorno e instalar `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Ejecución con Docker:

```powershell
docker build -t navirag-trading .
docker run --rm -p 8501:8501 --env-file .env navirag-trading
```

La configuración de MongoDB, creación del índice e ingesta se mantiene en [COMO_EJECUTAR.md](COMO_EJECUTAR.md).

## LangGraph

`langgraph.json` registra el grafo con la ruta confirmada:

```text
./agent_app/agent.py:graph
```

## Evaluación EV2

Los casos funcionales, de memoria, continuidad y errores inyectados se definen en `eval/casos_ev2.json`. El runner está en `eval/run_casos_ev2.py` y su output `eval/resultados_ev2.json` no se versiona.

La evidencia ejecutada no forma parte de este README y se incorporará posteriormente al informe mediante screenshots.

## Límites

- No usa datos de mercado en tiempo real.
- No ejecuta órdenes ni backtesting.
- No entrega asesoría financiera directa.
- `MemorySaver` e `InMemoryStore` viven en el proceso actual y no ofrecen persistencia durable tras reiniciar la aplicación.
