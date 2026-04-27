"""Prepare RAGAS evaluation for NaviRag Trading.

This script is intentionally conservative: ``--dry-run`` validates the dataset
and imports without calling retrieval, generation, MongoDB, GitHub Models or
RAGAS scorers. Real evaluation must be requested explicitly in a later run.
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATASET_PATH = Path(__file__).with_name("dataset.json")
RESULTS_MD_PATH = Path(__file__).with_name("evaluation_results.md")
RESULTS_CSV_PATH = Path(__file__).with_name("ragas_results.csv")
RAGAS_METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]
GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"


class RagasLegacyEmbeddingAdapter:
    """Expose legacy RAGAS embedding methods over a modern RAGAS embedder."""

    def __init__(self, embeddings: Any):
        self.embeddings = embeddings
        self.model = getattr(embeddings, "model", None)

    def embed_query(self, text: str) -> list[float]:
        """Embed one query using the underlying GitHub Models embedder."""
        return self.embeddings.embed_text(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using the underlying GitHub Models embedder."""
        return self.embeddings.embed_texts(texts)

    async def aembed_query(self, text: str) -> list[float]:
        """Async query embedding for RAGAS metrics that request it."""
        return await self.embeddings.aembed_text(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async batch embedding for RAGAS metrics that request it."""
        return await self.embeddings.aembed_texts(texts)


def load_dataset(dataset_path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    """Load and validate evaluation questions."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise ValueError("El dataset debe ser una lista de preguntas.")

    required_fields = {"id", "question", "ground_truth"}
    for index, item in enumerate(dataset, start=1):
        missing_fields = sorted(required_fields - set(item))
        if missing_fields:
            raise ValueError(
                f"Pregunta {index} sin campos requeridos: {', '.join(missing_fields)}"
            )
        if not item["question"].strip() or not item["ground_truth"].strip():
            raise ValueError(f"Pregunta {index} tiene question o ground_truth vacio.")

    return dataset


def limit_dataset(dataset: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    """Return a limited dataset for controlled runs."""
    if limit is None:
        return dataset
    if limit < 1:
        raise ValueError("--limit debe ser mayor o igual a 1.")
    return dataset[:limit]


def github_models_base_url(*endpoints: str | None) -> str:
    """Derive the OpenAI-compatible base URL used by GitHub Models."""
    for endpoint in endpoints:
        if not endpoint:
            continue
        if endpoint.endswith("/chat/completions"):
            return endpoint[: -len("/chat/completions")]
        if endpoint.endswith("/embeddings"):
            return endpoint[: -len("/embeddings")]
    return GITHUB_MODELS_BASE_URL


def parse_metric_names(metrics_arg: str) -> list[str]:
    """Parse and validate the requested RAGAS metric names."""
    metric_names = [name.strip() for name in metrics_arg.split(",") if name.strip()]
    if not metric_names:
        raise ValueError("--metrics debe incluir al menos una metrica o 'all'.")
    if "all" in metric_names:
        if len(metric_names) > 1:
            raise ValueError("--metrics all no se puede combinar con otras metricas.")
        return RAGAS_METRICS.copy()

    invalid_metrics = sorted(set(metric_names) - set(RAGAS_METRICS))
    if invalid_metrics:
        valid_metrics = ", ".join(["all", *RAGAS_METRICS])
        raise ValueError(
            "Metricas invalidas en --metrics: "
            f"{', '.join(invalid_metrics)}. Valores validos: {valid_metrics}."
        )

    selected_metrics = []
    for metric_name in metric_names:
        if metric_name not in selected_metrics:
            selected_metrics.append(metric_name)
    return selected_metrics


def is_numeric_score(value: Any) -> bool:
    """Return True only for real numeric, non-NaN metric scores."""
    if value is None:
        return False
    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def format_score(value: Any) -> str:
    """Format a metric score without inventing missing values."""
    if value is None:
        return ""
    if not is_numeric_score(value):
        return "nan"
    return str(round(float(value), 4))


def build_evaluation_rows(
    dataset: list[dict[str, Any]],
    top_k: int,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Run the NaviRag RAG pipeline and build rows for RAGAS."""
    from src.generate.generate import RAGGenerator
    from src.retrieval.retrieval import Retriever

    retriever = Retriever()
    generator = RAGGenerator()
    rows = []

    for item in limit_dataset(dataset, limit):
        question = item["question"]
        chunks = retriever.retrieve(question, top_k=top_k)
        response = generator.generate(question=question, chunks=chunks)
        contexts = [chunk.get("text", "") for chunk in chunks if chunk.get("text")]

        rows.append(
            {
                "id": item["id"],
                "type": item.get("type", "ragas"),
                "question": question,
                "answer": response["answer"],
                "contexts": contexts,
                "ground_truth": item["ground_truth"],
                "sources": [
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "file": chunk.get("file"),
                        "page": chunk.get("page"),
                        "section": chunk.get("section"),
                        "score": chunk.get("score"),
                    }
                    for chunk in chunks
                ],
            }
        )

    return rows


def build_ragas_adapters() -> tuple[Any, Any]:
    """Build RAGAS-compatible GitHub Models adapters without changing providers."""
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    from ragas.embeddings.base import embedding_factory
    from ragas.llms.base import llm_factory
    from src.utils.embeddings import (
        DEFAULT_GITHUB_EMBEDDING_MODEL,
        DEFAULT_GITHUB_EMBEDDINGS_ENDPOINT,
    )
    from src.utils.llm import DEFAULT_GITHUB_CHAT_ENDPOINT, DEFAULT_GITHUB_CHAT_MODEL

    load_dotenv()
    api_key = os.getenv("GITHUB_TOKEN")
    if not api_key:
        raise RuntimeError("Falta GITHUB_TOKEN en el entorno. Configura .env.")

    chat_model = os.getenv("GITHUB_CHAT_MODEL") or DEFAULT_GITHUB_CHAT_MODEL
    embedding_model = (
        os.getenv("GITHUB_EMBEDDING_MODEL") or DEFAULT_GITHUB_EMBEDDING_MODEL
    )
    base_url = github_models_base_url(
        os.getenv("GITHUB_MODELS_CHAT_ENDPOINT") or DEFAULT_GITHUB_CHAT_ENDPOINT,
        os.getenv("GITHUB_MODELS_EMBEDDINGS_ENDPOINT")
        or DEFAULT_GITHUB_EMBEDDINGS_ENDPOINT,
    )
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    llm = llm_factory(chat_model, provider="openai", client=client)
    embeddings = embedding_factory(
        provider="openai",
        model=embedding_model,
        client=client,
    )
    return llm, RagasLegacyEmbeddingAdapter(embeddings)


def load_ragas_metrics(
    metric_names: list[str] | None = None,
    llm: Any | None = None,
    embeddings: Any | None = None,
) -> list[Any]:
    """Load RAGAS metrics compatible with ragas.evaluate()."""
    try:
        from ragas.metrics._answer_relevance import answer_relevancy
        from ragas.metrics._context_precision import context_precision
        from ragas.metrics._context_recall import context_recall
        from ragas.metrics._faithfulness import faithfulness
    except ImportError as error:
        raise RuntimeError(
            "Falta RAGAS. Instala dependencias con 'pip install -r requirements.txt'."
        ) from error

    if llm is None or embeddings is None:
        llm, embeddings = build_ragas_adapters()

    requested_metrics = metric_names or RAGAS_METRICS
    metrics_by_name = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }
    metrics = [metrics_by_name[metric_name] for metric_name in requested_metrics]
    for metric in metrics:
        if llm is not None and hasattr(metric, "llm"):
            metric.llm = llm
        if embeddings is not None and hasattr(metric, "embeddings"):
            metric.embeddings = embeddings
    validate_ragas_metrics(metrics)
    return metrics


def validate_ragas_metrics(metrics: list[Any]) -> None:
    """Fail early if metrics are not accepted by ragas.evaluate()."""
    try:
        from ragas.metrics.base import Metric
    except ImportError as error:
        raise RuntimeError(
            "Falta RAGAS. Instala dependencias con 'pip install -r requirements.txt'."
        ) from error

    invalid_metrics = []
    for metric in metrics:
        if not isinstance(metric, Metric):
            metric_name = getattr(metric, "name", "<sin nombre>")
            mro = " -> ".join(cls.__name__ for cls in metric.__class__.__mro__)
            invalid_metrics.append(
                f"{metric_name}: {metric.__class__.__name__} ({mro})"
            )

    if invalid_metrics:
        details = "; ".join(invalid_metrics)
        raise TypeError(
            "ragas.evaluate() requiere objetos inicializados que hereden de "
            f"ragas.metrics.base.Metric. Metricas invalidas: {details}"
        )


def score_with_ragas(
    rows: list[dict[str, Any]],
    metric_names: list[str],
    max_workers: int,
    timeout: int,
) -> list[dict[str, Any]]:
    """Run real RAGAS scoring using GitHub Models adapters."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.run_config import RunConfig

    llm, embeddings = build_ragas_adapters()
    metrics = load_ragas_metrics(
        metric_names=metric_names,
        llm=llm,
        embeddings=embeddings,
    )
    validate_ragas_metrics(metrics)
    dataset = Dataset.from_list(
        [
            {
                "user_input": row["question"],
                "response": row["answer"],
                "retrieved_contexts": row["contexts"],
                "reference": row["ground_truth"],
            }
            for row in rows
        ]
    )
    result = evaluate(
        dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(timeout=timeout, max_workers=max_workers),
        show_progress=True,
    )
    scores_frame = result.to_pandas()
    scored_rows = []
    for row, (_, score_row) in zip(rows, scores_frame.iterrows(), strict=True):
        scores = {
            metric_name: score_row.get(metric_name)
            for metric_name in metric_names
            if metric_name in score_row
        }
        scored_rows.append({**row, "scores": scores})
    return scored_rows


def write_markdown_report(
    rows: list[dict[str, Any]],
    metric_names: list[str] | None = None,
    output_path: Path = RESULTS_MD_PATH,
    dry_run: bool = False,
) -> None:
    """Write a Markdown evaluation report without inventing metric results."""
    selected_metrics = metric_names or RAGAS_METRICS
    lines = [
        "# Evaluacion RAGAS NaviRag Trading",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Estado",
        "",
    ]
    if dry_run:
        lines.append("Dry-run ejecutado: no se llamo retrieval, generacion, MongoDB, GitHub Models ni RAGAS.")
    else:
        has_scores = any(row.get("scores") for row in rows)
        if has_scores:
            lines.append("Evaluacion RAGAS real ejecutada explicitamente.")
        else:
            lines.append("Pipeline ejecutado para preparar filas. Scores RAGAS reales pendientes.")

    lines.extend(
        [
            "",
            "## Metricas RAGAS solicitadas",
            "",
            *[f"- {metric_name}" for metric_name in selected_metrics],
            "",
            "## Casos",
            "",
            f"| id | tipo | pregunta | estado | {' | '.join(selected_metrics)} |",
            f"| --- | --- | --- | --- | {' | '.join(['---:'] * len(selected_metrics))} |",
        ]
    )
    for row in rows:
        question = row["question"].replace("|", "\\|")
        status = "dataset validado" if dry_run else "fila preparada"
        scores = row.get("scores", {})
        if scores and all(is_numeric_score(scores.get(metric)) for metric in selected_metrics):
            status = "score completo"
        elif scores:
            status = "score parcial"
        metric_values = [format_score(scores.get(metric)) for metric in selected_metrics]
        lines.append(
            f"| {row['id']} | {row.get('type', '')} | {question} | {status} | "
            f"{' | '.join(metric_values)} |"
        )

    lines.extend(
        [
            "",
            "## Compatibilidad",
            "",
            "No inventar resultados. Si una metrica queda `nan`, la ejecucion debe tratarse como parcial.",
            "`eval/evaluate.py` prepara adaptadores RAGAS usando `AsyncOpenAI` como cliente compatible contra GitHub Models,",
            "sin agregar `OPENAI_API_KEY` ni cambiar proveedor.",
            "",
            "Ejemplos de ejecucion real controlada:",
            "",
            "```bash",
            "python eval/evaluate.py --prepare-rows --run-ragas --limit 1 --metrics context_recall",
            "python eval/evaluate.py --prepare-rows --run-ragas --limit 1 --metrics answer_relevancy",
            "```",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv_rows(
    rows: list[dict[str, Any]],
    metric_names: list[str] | None = None,
    output_path: Path = RESULTS_CSV_PATH,
) -> None:
    """Write prepared rows for audit/debugging without RAGAS scores."""
    selected_metrics = metric_names or RAGAS_METRICS
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "type",
                "question",
                "answer",
                "ground_truth",
                "contexts",
                *selected_metrics,
            ],
        )
        writer.writeheader()
        for row in rows:
            output_row = {
                "id": row["id"],
                "type": row.get("type", ""),
                "question": row["question"],
                "answer": row.get("answer", ""),
                "ground_truth": row["ground_truth"],
                "contexts": json.dumps(row.get("contexts", []), ensure_ascii=False),
            }
            scores = row.get("scores", {})
            output_row.update(
                {metric: format_score(scores.get(metric)) for metric in selected_metrics}
            )
            writer.writerow(output_row)


def run_dry_run(dataset: list[dict[str, Any]], metric_names: list[str]) -> None:
    """Validate dataset and imports without executing the RAG pipeline."""
    from src.generate.generate import RAGGenerator  # noqa: F401
    from src.retrieval.retrieval import Retriever  # noqa: F401

    print(f"dataset_questions={len(dataset)}")
    print(f"metrics={','.join(metric_names)}")
    print("pipeline_imports=ok")
    print("dry_run=no_retrieval_no_generation_no_ragas")
    print("dry_run=no_result_files_updated")
    print(f"report={RESULTS_MD_PATH}")
    print(f"csv={RESULTS_CSV_PATH}")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Prepara evaluacion RAGAS NaviRag.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="Ruta al dataset JSON de evaluacion.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Cantidad de chunks a recuperar por pregunta en ejecucion real.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita cantidad de preguntas para pruebas controladas.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida dataset e imports sin llamar retrieval, generacion ni RAGAS.",
    )
    parser.add_argument(
        "--prepare-rows",
        action="store_true",
        help="Ejecuta retrieval/generacion y guarda filas sin calcular scores RAGAS.",
    )
    parser.add_argument(
        "--run-ragas",
        action="store_true",
        help="Intenta calcular scores RAGAS. Requiere adaptador LLM/embeddings compatible.",
    )
    parser.add_argument(
        "--metrics",
        default="all",
        help=(
            "Metricas RAGAS a ejecutar: all o lista separada por coma con "
            "faithfulness, answer_relevancy, context_precision, context_recall."
        ),
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Maximo de workers para RAGAS RunConfig. Default: 1.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout en segundos para RAGAS RunConfig. Default: 180.",
    )
    return parser.parse_args()


def main() -> None:
    """Run evaluation preparation."""
    args = parse_args()
    dataset = load_dataset(args.dataset)
    metric_names = parse_metric_names(args.metrics)

    if args.max_workers < 1:
        raise SystemExit("--max-workers debe ser mayor o igual a 1.")
    if args.timeout < 1:
        raise SystemExit("--timeout debe ser mayor o igual a 1.")

    if args.dry_run:
        run_dry_run(dataset, metric_names=metric_names)
        return

    if not args.prepare_rows and not args.run_ragas:
        raise SystemExit("Usa --dry-run, --prepare-rows o --run-ragas.")

    rows = build_evaluation_rows(dataset=dataset, top_k=args.top_k, limit=args.limit)
    if args.run_ragas:
        rows = score_with_ragas(
            rows,
            metric_names=metric_names,
            max_workers=args.max_workers,
            timeout=args.timeout,
        )

    write_markdown_report(rows, metric_names=metric_names)
    write_csv_rows(rows, metric_names=metric_names)

    print(f"prepared_rows={len(rows)}")
    print(f"metrics={','.join(metric_names)}")
    print(f"max_workers={args.max_workers}")
    print(f"timeout={args.timeout}")
    print(f"report={RESULTS_MD_PATH}")
    print(f"csv={RESULTS_CSV_PATH}")


if __name__ == "__main__":
    main()
