# Decisiones técnicas

## Streamlit

La demo se orienta a Streamlit porque permite construir una interfaz académica simple, rápida de ejecutar y fácil de explicar.

## Datos locales

Los PDFs se cargarán manualmente en `data/raw/`. No se integran APIs de precios, brokers, exchanges ni fuentes financieras externas.

## Segmentación

La estrategia futura priorizará fragmentos interpretables y trazables por documento, página, título, sección, concepto o unidad temática. Si un PDF no tiene estructura clara, se podrá usar segmentación por tamaño con solapamiento moderado, documentando la limitación.

## Vector store

El repositorio deja preparada la carpeta `data/vectorstore/` para un almacenamiento local futuro. Todavía no se implementa indexación real.

## Seguridad

`src/safety.py` contiene una detección inicial por palabras clave para bloquear preguntas de compra, venta, señales, predicciones o asesoría financiera. Esta regla es mínima y deberá reforzarse cuando se implemente el flujo completo.

## Generación

El prompt base está definido en `src/prompts.py` y exige responder solo con contexto recuperado. La generación real con LLM queda pendiente para una etapa posterior.
