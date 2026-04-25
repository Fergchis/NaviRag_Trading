"""Local cosine-similarity retrieval for NaviRag Trading."""

import argparse
import json
import math
from pathlib import Path
from typing import Any

from src.config import VECTORSTORE_DIR
from src.embeddings import load_embedding_config, request_embeddings

EMBEDDINGS_FILE = VECTORSTORE_DIR / "embeddings.json"


def load_embedding_records(input_file: Path = EMBEDDINGS_FILE) -> list[dict]:
    """Load locally stored chunk embeddings."""
    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe {input_file}. Ejecuta primero: python -m src.embeddings"
        )

    payload = json.loads(input_file.read_text(encoding="utf-8"))
    return payload.get("embeddings", [])


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def embed_query(question: str) -> list[float]:
    """Generate an embedding for a user question."""
    config = load_embedding_config()
    embeddings = request_embeddings(
        texts=[question],
        token=config["token"],
        endpoint=config["endpoint"],
        model=config["model"],
    )
    return embeddings[0]


def retrieve(question: str, top_k: int = 3) -> list[dict]:
    """Retrieve top-k chunks using local cosine similarity."""
    records = load_embedding_records()
    query_embedding = embed_query(question)
    scored_results = []

    for record in records:
        score = cosine_similarity(query_embedding, record.get("embedding", []))
        scored_results.append(
            {
                "chunk_id": record.get("chunk_id"),
                "file": record.get("file"),
                "page": record.get("page"),
                "page_chunk_index": record.get("page_chunk_index"),
                "text": record.get("text"),
                "score": score,
            }
        )

    scored_results.sort(key=lambda item: item["score"], reverse=True)
    return scored_results[:top_k]


def retrieve_placeholder_context(question: str) -> list[dict]:
    """Return placeholder context for the Streamlit placeholder app."""
    return [
        {
            "question": question,
            "message": "Retrieval real disponible por CLI con python -m src.retrieval.",
        }
    ]


def parse_args() -> Any:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Recupera chunks por similitud coseno.")
    parser.add_argument("question", help="Pregunta educativa para buscar contexto.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Cantidad de chunks relevantes a mostrar.",
    )
    return parser.parse_args()


def main() -> None:
    """Run retrieval from the command line."""
    args = parse_args()
    results = retrieve(question=args.question, top_k=args.top_k)

    print(f"Pregunta: {args.question}")
    for index, result in enumerate(results, start=1):
        text = result.get("text", "").replace("\n", " ")[:300]
        print("---")
        print(f"Resultado {index}")
        print(f"score: {result['score']:.4f}")
        print(f"chunk_id: {result['chunk_id']}")
        print(f"file: {result['file']}")
        print(f"page: {result['page']}")
        print(f"page_chunk_index: {result['page_chunk_index']}")
        print(f"text: {text}")


if __name__ == "__main__":
    main()
