# Decisiones tecnicas

## Streamlit

Se usa Streamlit porque permite ejecutar una demo academica local con baja friccion, mostrar la pregunta, la respuesta y las fuentes recuperadas en una misma interfaz, y explicar el flujo RAG sin infraestructura adicional.

## MongoDB Atlas Vector Search

MongoDB Atlas Vector Search se usa como vectorstore principal para acercar la arquitectura a los ejemplos de Clase 1.4. La base configurada por defecto es `navirag` y cada documento conserva `chunk_id`, texto, embedding, modelo y metadatos trazables como archivo, pagina e indice de chunk.

El JSON local en `data/vectorstore/embeddings.json` puede mantenerse como artefacto historico ignorado por Git, pero no forma parte del runtime de retrieval.

La limitacion es clara: Atlas requiere configuracion externa, variables locales y un indice vectorial creado en la coleccion.

## Similitud coseno

El retrieval usa `$vectorSearch` en MongoDB Atlas con similitud coseno porque compara la orientacion entre vectores de embeddings y es una metrica estandar para recuperar texto semanticamente cercano.

El indice vectorial configurado usa el campo `embedding`, 1536 dimensiones y similitud coseno.

## Alineacion con ejemplos de clase basados en MongoDB Atlas

Los ejemplos de clase usan MongoDB Atlas para busqueda vectorial. NaviRag Trading adopta ese enfoque como unico vectorstore operativo.

La migracion aun no elimina los artefactos JSON fisicos para evitar perder evidencia local.

## Sin mercado en vivo

No se integran APIs de precios, brokers, exchanges ni noticias en tiempo real. El objetivo es consultar material educativo cargado por el usuario, no responder sobre condiciones actuales del mercado.

Incluir mercado en vivo cambiaria el alcance hacia un sistema financiero operativo, con riesgos de exactitud, latencia, cumplimiento y responsabilidad que no corresponden a la demo academica.

## Sin backtesting

No se implementa backtesting porque el proyecto no evalua estrategias de trading ni simula operaciones. El flujo actual recupera y explica fragmentos de documentos; no calcula rendimiento historico, drawdown, entradas, salidas ni reglas de ejecucion.

Agregar backtesting implicaria otra categoria de sistema, datos historicos consistentes y validacion metodologica adicional.

## Datos no versionados

No se suben PDFs, `documents.json`, `chunks.json`, `embeddings.json`, vectorstores ni logs porque pueden contener material privado, datos pesados, evidencia local o contenido de clase. Esos archivos deben permanecer en carpetas ignoradas por Git.

El repositorio versiona codigo, documentacion, configuracion de ejemplo y estructura minima con `.gitkeep`, no el corpus ni los artefactos derivados.

## Vectorstore parcial

La evidencia local indica:

- PDFs procesados: 3
- Paginas extraidas: 583
- Chunks generados: 1046
- Embeddings generados: 200
- Modelo de embeddings: `openai/text-embedding-3-small`

El vectorstore es parcial. Esto es suficiente para una demo academica si se declara explicitamente y las pruebas se formulan como validacion del flujo implementado, no como cobertura completa del corpus.
