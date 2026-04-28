import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


class MongoDBClient:
    def __init__(self, db_name: str | None = None):
        self.client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
        self.db = self.client[db_name or os.getenv("MONGODB_DATABASE", "navirag")]
        self.collection_name = os.getenv("MONGODB_COLLECTION", "embeddings")
        self.index_name = os.getenv("MONGODB_VECTOR_INDEX", "vector_index")

    def get_collection(self, collection_name: str | None = None):
        return self.db[collection_name or self.collection_name]

    def upsert_embedding_records(self, records: list[dict]) -> int:
        collection = self.get_collection()
        written = 0

        for record in records:
            document = {
                "chunk_id": record.get("chunk_id"),
                "text": record.get("text"),
                "embedding": record.get("embedding"),
                "embedding_model": record.get("embedding_model"),
                "metadata": {
                    "file": record.get("file"),
                    "page": record.get("page"),
                    "section": record.get("section"),
                    "page_chunk_index": record.get("page_chunk_index"),
                    "character_count": record.get("character_count"),
                },
            }
            collection.update_one(
                {"chunk_id": record.get("chunk_id")},
                {"$set": document},
                upsert=True,
            )
            written += 1

        return written

    def delete_all_documents(self) -> int:
        result = self.get_collection().delete_many({})
        return result.deleted_count

    def get_existing_chunk_ids(self) -> set[str]:
        documents = self.get_collection().find(
            {"chunk_id": {"$exists": True}},
            {"_id": 0, "chunk_id": 1},
        )
        return {document["chunk_id"] for document in documents}

    def vector_search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        results = self.get_collection().aggregate([
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
                    "embedding_model": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ])

        return list(results)
