import os

from src.utils.mongodb import MongoDBClient

mongo = MongoDBClient()
collection = mongo.get_collection()

collection.create_search_index({
    "name": os.getenv("MONGODB_VECTOR_INDEX", "vector_index"),
    "type": "vectorSearch",
    "definition": {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": 1536,
                "similarity": "cosine",
            }
        ]
    },
})

print("Vector search index created.")
