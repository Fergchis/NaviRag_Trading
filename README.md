# NaviRag Trading

Demo RAG educativa para **Iwakura Trading Academy** orientada a consultar PDFs de trading con trazabilidad documental.

Esta primera versión solo crea la estructura base del repositorio y placeholders mínimos. No implementa señales de trading, recomendaciones financieras, asesoría de inversión, datos de mercado en vivo ni backtesting real.

## Alcance actual

- Aplicación base en Streamlit.
- Estructura modular en `src/`.
- Carpetas preparadas para datos crudos, procesados y vector store local.
- Stubs para ingesta, segmentación, embeddings, retrieval, generación y seguridad.
- Documentación técnica mínima.
- Preguntas iniciales de evaluación.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Ejecución con Docker

```bash
docker build -t navirag-trading .
docker run -p 8501:8501 navirag-trading
```

Luego abre `http://localhost:8501`.

## Estructura

```text
data/raw/          PDFs cargados manualmente
data/processed/    salidas intermedias futuras
data/vectorstore/  vector store local futuro
src/               módulos de la aplicación
eval/              preguntas y resultados de evaluación
docs/              diseño, arquitectura y decisiones técnicas
```

## Restricciones

NaviRag Trading tiene fines académicos. El sistema debe responder solo con información respaldada por documentos cargados y rechazar solicitudes de compra, venta, predicción, entradas, salidas, stop loss, take profit o asesoría financiera personalizada.
