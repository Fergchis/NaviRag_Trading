# Evaluacion RAGAS NaviRag Trading

## Estado

RAGAS queda integrado como evaluacion complementaria y manual, alineada con el enfoque simple de Clase 1.4:

- dataset pequeno en `eval/dataset.json`;
- script de evaluacion en `eval/evaluate.py`;
- ejecucion explicita por consola;
- resultados parciales reales sin presentarlos como evaluacion completa.

No forma parte del runtime de Streamlit y no reemplaza la validacion funcional de la demo.

El script actual vuelve al estilo simple de Clase 1.4: sin CLI, sin reportes avanzados y con `run_evaluation(limit=1)` por defecto.

## Resultado preservado

La evidencia actualmente preservada corresponde a una prueba real controlada de una pregunta sobre `RAGAS-01`.

| metrica | estado | resultado |
| --- | --- | --- |
| context_precision | ejecutada y preservada | 1.0 |
| context_recall | ejecutada previamente | no preservado en los archivos actuales |
| faithfulness | ejecutada previamente | valor no preservado en los archivos actuales |
| answer_relevancy | timeout con GitHub Models | pendiente |

## Caso preservado

| id | tipo | pregunta | estado | context_precision |
| --- | --- | --- | --- | ---: |
| RAGAS-01 | risk_management | Que dice el material sobre gestion de riesgo en trading algoritmico? | score completo para la metrica solicitada | 1.0 |

## Limitaciones

La evaluacion completa de las 8 preguntas queda pendiente.

Los resultados anteriores de `context_recall` y `faithfulness` no se reconstruyen ni se inventan en este reporte si no estan preservados en `eval/ragas_results.csv` o en este Markdown.

`answer_relevancy` presento timeouts al ejecutarse con GitHub Models. Por eso se mantiene como metrica pendiente o limitada para esta entrega.

## Ejecucion recomendada

Prueba real controlada por defecto:

```bash
python eval/evaluate.py
```

No se debe interpretar este resultado parcial como una evaluacion completa de todas las metricas ni de todo el dataset.
