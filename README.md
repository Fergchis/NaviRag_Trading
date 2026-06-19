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

El supervisor selecciona `rag_agent`, `memory_agent`, `answer_agent`, `rag_then_answer` o `FINISH`. El agente RAG contiene un subgrafo con reformulación de consulta, `ToolNode` y `rag_search`. El agente de memoria usa `save_memory` y `search_memory`. La memoria conversacional usa `MemorySaver` y la memoria entre conversaciones usa `InMemoryStore`.

La descripción completa de nodos, edges, rutas, tools y evidencia EV2 está en [docs/flujo_langgraph_ev2.md](docs/flujo_langgraph_ev2.md).

## Requisitos

- Python 3.11 o Docker.
- Token con acceso a GitHub Models.
- MongoDB Atlas con la colección documental y el índice vectorial configurados.
- Dependencias declaradas en `requirements.txt`.

## Ejecucion

Leer archivo "COMO_EJECUTAR.md", esta en la raiz del proyecto.

## LangGraph

`langgraph.json` registra el grafo con la ruta confirmada:

```text
./agent_app/agent.py:graph
```

## Límites

- No usa datos de mercado en tiempo real.
- No ejecuta órdenes ni backtesting.
- No entrega asesoría financiera directa.
- `MemorySaver` e `InMemoryStore` viven en el proceso actual y no ofrecen persistencia durable tras reiniciar la aplicación.
