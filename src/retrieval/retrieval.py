"""MongoDB Atlas Vector Search retrieval for NaviRag Trading."""

import argparse
from typing import Any

from src.utils.embeddings import EmbeddingClient
from src.utils.mongodb import MongoDBClient


class Retriever:
    """Retriever backed by MongoDB Atlas Vector Search."""

    def __init__(
        self,
        embedder: EmbeddingClient | None = None,
        mongo_client: MongoDBClient | None = None,
    ) -> None:
        self.embedder = embedder or EmbeddingClient()
        self.mongo_client = mongo_client or MongoDBClient()

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """Retrieve top-k chunks using MongoDB Atlas Vector Search."""
        query_embedding = self.embedder.get_embedding(query)
        results = self.mongo_client.vector_search(
            query_embedding=query_embedding,
            top_k=top_k,
        )
        return [
            {
                "chunk_id": result.get("chunk_id"),
                "file": (result.get("metadata") or {}).get("file"),
                "page": (result.get("metadata") or {}).get("page"),
                "page_chunk_index": (result.get("metadata") or {}).get(
                    "page_chunk_index"
                ),
                "text": result.get("text"),
                "score": result.get("score", 0),
            }
            for result in results
        ]


def parse_args() -> Any:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Recupera chunks con MongoDB Atlas Vector Search."
    )
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
    results = Retriever().retrieve(query=args.question, top_k=args.top_k)

    print(f"Pregunta: {args.question}")
    print("retrieval_source=mongodb")
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
