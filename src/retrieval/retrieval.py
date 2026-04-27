from src.utils.embeddings import EmbeddingClient
from src.utils.mongodb import MongoDBClient


class Retriever:
    def __init__(self):
        self.embedder = EmbeddingClient()
        self.mongo = MongoDBClient()

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        query_embedding = self.embedder.get_embedding(query)
        results = self.mongo.vector_search(query_embedding=query_embedding, top_k=top_k)

        return [
            {
                "chunk_id": result.get("chunk_id"),
                "file": (result.get("metadata") or {}).get("file"),
                "page": (result.get("metadata") or {}).get("page"),
                "section": (result.get("metadata") or {}).get("section"),
                "page_chunk_index": (result.get("metadata") or {}).get("page_chunk_index"),
                "text": result.get("text"),
                "score": result.get("score", 0),
            }
            for result in results
        ]
