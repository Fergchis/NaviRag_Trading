# NaviRAG Trading

NaviRAG Trading es un agente educativo para consultar documentos PDF sobre trading. Usa LangGraph para coordinar agentes especializados, MongoDB Atlas Vector Search para recuperar contexto, GitHub Models para embeddings y respuestas, y Supabase + Power BI para observabilidad EV3.

El sistema no ejecuta operaciones ni entrega recomendaciones financieras directas, señales de compra o venta ni instrucciones de inversión.

## Entrega EV3

La versión principal de esta rama es EV3. NaviRAG registra sesiones, mensajes, trazas y costos en Supabase, y Power BI consume esas tablas para visualizar métricas de latencia, tokens, costos, sesiones, mensajes y trazas.

Archivos principales de la migración EV3:

- `schema.sql`: crea las tablas de observabilidad en Supabase.
- `src/observability/supabase_logger.py`: registra sesiones, mensajes, trazas y costos.
- `GUIA_POWERBI.md`: explica cómo crear el proyecto Supabase, ejecutar `schema.sql`, conectar Power BI y construir el dashboard.
- `PowerBI.pbix`: archivo local del informe Power BI. Está ignorado por Git y no se versiona.

## Arquitectura

```text
Usuario
  └── Streamlit
        ├── LangGraph
        │     ├── supervisor
        │     ├── rag_agent     → recuperación documental
        │     ├── memory_agent  → memoria long-term
        │     └── answer_agent  → respuesta final
        └── Supabase            → sesiones, mensajes, trazas y costos
                └── Power BI    → dashboard EV3
```

El supervisor selecciona `rag_agent`, `memory_agent`, `answer_agent`, `rag_then_answer` o `FINISH`. El agente RAG contiene un subgrafo con reformulación de consulta, `ToolNode` y `rag_search`. El agente de memoria usa las tools de LangMem `manage_memory` y `search_memory`. La memoria conversacional usa `MemorySaver` y la memoria entre conversaciones usa `InMemoryStore`.

## Requisitos

- Python 3.11 o Docker.
- Token con acceso a GitHub Models.
- MongoDB Atlas con corpus PDF ingerido, colección documental e índice vectorial configurados.
- Supabase con las tablas creadas mediante `schema.sql`.
- Power BI Desktop para construir o abrir el informe de observabilidad.
- Dependencias declaradas en `requirements.txt`.

## Ejecución

La configuración completa para `.env`, MongoDB Atlas, ingesta, Streamlit, Docker y evaluación EV3 está en [COMO_EJECUTAR.md](COMO_EJECUTAR.md).

La configuración de Supabase + Power BI está en [GUIA_POWERBI.md](GUIA_POWERBI.md).

## Observabilidad EV3

NaviRAG espera estas variables en el `.env` local:

```env
SUPABASE_URL=
SUPABASE_KEY=
```

`schema.sql` debe ejecutarse en Supabase antes de usar el dashboard. La app registra observabilidad de forma best-effort: si Supabase falla, el chat puede continuar sin detener la respuesta del agente.

## Evaluación EV3

Los casos EV3 están definidos en [eval/casos_ev3.json](eval/casos_ev3.json), se ejecutan mediante [eval/run_casos_ev3.py](eval/run_casos_ev3.py) y el snapshot de resultados se conserva en [eval/resultados_ev3.json](eval/resultados_ev3.json).

La evaluación EV3 del directorio `eval/` no reemplaza ni alimenta automáticamente la tabla `evaluations` de Supabase. Esa tabla queda disponible para feedback futuro siguiendo el esquema de clase.

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
