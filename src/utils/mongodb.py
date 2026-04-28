import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()


class MongoDBClient:
    def __init__(self, db_name: str | None = None):
        self.client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
        self.db = self.client[db_name or os.getenv("MONGODB_DATABASE", "navirag")]

    def get_collection(self, collection_name: str | None = None) -> Collection:
        return self.db[collection_name or os.getenv("MONGODB_COLLECTION", "embeddings")]
