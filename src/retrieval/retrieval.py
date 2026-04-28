import os

from src.utils.embeddings import EmbeddingClient
from src.utils.mongodb import MongoDBClient


class Retriever:
    def __init__(
        self,
        db_name: str | None = None,
        collection_name: str | None = None,
        index_name: str | None = None,
    ):
        self.embedder = EmbeddingClient()
        self.mongo = MongoDBClient(db_name)
        self.collection = self.mongo.get_collection(collection_name)
        self.index_name = index_name or os.getenv("MONGODB_VECTOR_INDEX", "vector_index")

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        query_embedding = self.embedder.get_embedding(query)

        results = self.collection.aggregate([
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": top_k * 10,
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "chunk_id": 1,
                    "text": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ])

        return list(results)
