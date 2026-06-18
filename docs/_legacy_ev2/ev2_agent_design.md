# Diseño técnico histórico del agente Ev2

> Documento histórico. Describe el planner fijo anterior y no representa el grafo activo.

La primera versión de la capa Ev2 envolvía el RAG existente con una secuencia fija:

```text
load_memory -> safety_check -> retrieve_context -> write_answer -> save_memory
```

Sus componentes eran `TradingAgent`, `AgentPlanner`, `AgentTools` y `AgentMemory`. El planner no usaba un LLM para decidir tools y las operaciones se ejecutaban en un orden predeterminado.

Esta descripción se conserva únicamente como registro histórico. La documentación vigente está en `docs/flujo_langgraph_ev2.md`.
