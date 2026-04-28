# Decisiones tecnicas

## Streamlit

Se usa Streamlit porque permite ejecutar una demo academica local con baja friccion, mostrar la pregunta, la respuesta y las fuentes recuperadas en una misma interfaz, y explicar el flujo RAG sin infraestructura adicional.

## MongoDB Atlas Vector Search

MongoDB Atlas Vector Search se usa como vectorstore principal para acercar la arquitectura a los ejemplos de Clase 1.4. La base configurada por defecto es `navirag` y cada documento conserva `chunk_id`, texto, embedding, modelo y metadatos trazables como archivo, pagina cuando exista, seccion e indice de chunk.

El JSON local en `data/vectorstore/embeddings.json` puede mantenerse como artefacto historico ignorado por Git, pero no forma parte del runtime de retrieval.

La limitacion es clara: Atlas requiere configuracion externa, variables locales y un indice vectorial creado en la coleccion con `python create_vector_index.py`.

La generacion normal de embeddings hace upsert incremental sobre la coleccion existente. Cuando cambian ingesta
o chunking, se debe usar `python -m src.utils.embeddings --rebuild-mongodb` para borrar la coleccion configurada
y reindexar todos los chunks actuales desde cero. El flag no se puede combinar con `--limit` para evitar una
coleccion reconstruida parcialmente.

Si la reconstruccion se interrumpe por rate limit despues de insertar parte de los chunks, se debe continuar con
`python -m src.utils.embeddings --resume-mongodb`. Ese modo consulta solo los `chunk_id` existentes en MongoDB,
omite chunks ya insertados y genera embeddings solo para los pendientes, sin borrar la coleccion.

## Ingesta PDF con MarkItDown

La ingesta usa `markitdown[pdf]` para convertir PDFs locales a texto sin OCR ni llamadas externas.
La API usada devuelve texto consolidado por documento, no paginas separadas. Para mantener trazabilidad honesta,
los registros de ingesta conservan archivo, ruta, `section="document"` y `page=None` en vez de inventar numeros
de pagina. Esa metadata se propaga a chunks, futuros records de embeddings, MongoDB y presentacion de fuentes.

El chunking se simplifica para seguir el estilo de Clase 1.4: divide el texto por tamaño fijo con overlap
(`chunk_size=2200`, `overlap=200`) y conserva metadata minima para trazabilidad.

## Similitud coseno

El retrieval usa `$vectorSearch` en MongoDB Atlas con similitud coseno porque compara la orientacion entre vectores de embeddings y es una metrica estandar para recuperar texto semanticamente cercano.

El indice vectorial configurado usa el campo `embedding`, 1536 dimensiones y similitud coseno.

## Generacion RAG

`RAGGenerator` sigue el patron de Clase 1.4: crea su propio `Retriever`, recupera chunks dentro de `generate(query, history, top_k)`, arma el contexto y llama al LLM. La diferencia necesaria es que NaviRag usa GitHub Models y mantiene el prompt educativo de trading.

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

## Evaluacion RAGAS

RAGAS se incorpora como evaluacion complementaria y manual, alineada con Clase 1.4, usando un dataset pequeno en
`eval/dataset.json` y un script separado `eval/evaluate.py`. Las metricas preparadas son `faithfulness`,
`answer_relevancy`, `context_precision` y `context_recall`.

La app y el retrieval no dependen de RAGAS para funcionar. El script sigue el estilo simple de Clase 1.4:
carga el dataset, crea el retriever y generador, configura GitHub Models para RAGAS, recorre preguntas, imprime scores
y muestra un resumen. Por defecto se llama como `run_evaluation(limit=1)`.

La referencia de clase usa RAGAS con cliente OpenAI directo. NaviRag mantiene GitHub Models y usa el cliente
`AsyncOpenAI` solo como capa compatible apuntando a `https://models.github.ai/inference`, con `GITHUB_TOKEN`.
No se agrega `OPENAI_API_KEY` ni se cambia proveedor.

La ejecucion acotada queda como el comportamiento por defecto:

```bash
python eval/evaluate.py
```

El resultado preservado actualmente es una prueba parcial con `context_precision=1.0` para `RAGAS-01`. No se afirma
evaluacion completa de las 8 preguntas ni de todas las metricas. `answer_relevancy` presento timeouts con GitHub
Models y queda documentada como limitacion.

## Vectorstore MongoDB

La evidencia local indica:

- PDFs procesados: 5
- Documentos extraidos: 5
- Chunks generados: 338
- Embeddings en MongoDB: 338
- Modelo de embeddings: `openai/text-embedding-3-small`

MongoDB Atlas fue reindexado con los chunks locales simplificados actuales. La cobertura depende del corpus local disponible y de que los artefactos no versionados se mantengan consistentes.
