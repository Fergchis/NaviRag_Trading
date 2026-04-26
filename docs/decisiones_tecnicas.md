# Decisiones tecnicas

## Streamlit

Se usa Streamlit porque permite ejecutar una demo academica local con baja friccion, mostrar la pregunta, la respuesta y las fuentes recuperadas en una misma interfaz, y explicar el flujo RAG sin infraestructura adicional.

## Vectorstore local JSON

El vectorstore se guarda como JSON local en `data/vectorstore/embeddings.json` para mantener la entrega auditable y simple. Cada registro conserva `chunk_id`, archivo, pagina, texto, metadatos y embedding.

Esta decision evita depender de servicios externos de almacenamiento durante la evaluacion academica. Tambien permite inspeccionar manualmente el resultado de ingesta, chunking y embeddings.

La limitacion es clara: JSON local no esta pensado para produccion, alta concurrencia, grandes volumenes ni busquedas vectoriales optimizadas.

## Similitud coseno

El retrieval usa similitud coseno porque compara la orientacion entre vectores de embeddings y es una metrica estandar para recuperar texto semanticamente cercano. Para una demo parcial con pocos cientos de embeddings, calcular la similitud en memoria es suficiente y facil de defender.

No se agregan indices vectoriales especializados porque el alcance no requiere optimizacion de escala.

## Diferencia con ejemplos de clase basados en MongoDB Atlas

Algunos ejemplos de clase pueden usar MongoDB Atlas u otros servicios administrados para busqueda vectorial. NaviRag Trading conserva un vectorstore local JSON porque la entrega prioriza reproducibilidad local, trazabilidad y minimo acoplamiento tecnologico.

La arquitectura podria migrar a un motor vectorial externo en una etapa futura, pero eso no forma parte de esta entrega.

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
