"""Safe MongoDB Atlas connection utilities for NaviRag Trading."""

import argparse
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from pymongo.errors import OperationFailure

DEFAULT_MONGODB_DATABASE = "navirag"
DEFAULT_MONGODB_COLLECTION = "embeddings"
DEFAULT_MONGODB_VECTOR_INDEX = "vector_index"
DEFAULT_VECTOR_DIMENSIONS = 1536


def _require_mongo_client() -> Any:
    """Import MongoDB dependencies only when MongoDB is used."""
    try:
        from pymongo import MongoClient
        import dns.resolver  # noqa: F401
    except ImportError as error:
        raise RuntimeError(
            "Falta la dependencia 'pymongo' o 'dnspython'. Instala dependencias con "
            "'pip install -r requirements.txt'."
        ) from error

    return MongoClient


@dataclass(frozen=True)
class MongoDBConfig:
    """MongoDB connection settings loaded from local environment variables."""

    connection_string: str
    database: str
    collection: str
    vector_index: str

    @classmethod
    def from_env(cls) -> "MongoDBConfig":
        """Load MongoDB configuration without exposing secrets."""
        load_dotenv()
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        if not connection_string:
            raise RuntimeError("Falta MONGODB_CONNECTION_STRING en el entorno.")

        return cls(
            connection_string=connection_string,
            database=os.getenv("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE),
            collection=os.getenv("MONGODB_COLLECTION", DEFAULT_MONGODB_COLLECTION),
            vector_index=os.getenv("MONGODB_VECTOR_INDEX", DEFAULT_MONGODB_VECTOR_INDEX),
        )


class MongoDBClient:
    """Small MongoDB Atlas client wrapper."""

    def __init__(self, config: MongoDBConfig | None = None) -> None:
        self.config = config or MongoDBConfig.from_env()
        MongoClient = _require_mongo_client()
        self.client = MongoClient(
            self.config.connection_string,
            serverSelectionTimeoutMS=5000,
        )

    def get_collection(self, collection_name: str | None = None) -> Any:
        """Return the configured collection handle."""
        return self.client[self.config.database][collection_name or self.config.collection]

    def ensure_collection(self) -> Any:
        """Create the configured collection when it does not exist yet."""
        database = self.client[self.config.database]
        if self.config.collection not in database.list_collection_names():
            database.create_collection(self.config.collection)
        return database[self.config.collection]

    def ping(self) -> bool:
        """Validate connectivity with a MongoDB ping command."""
        self.client.admin.command("ping")
        return True

    def upsert_embedding_records(self, records: list[dict]) -> int:
        """Upsert embedding records into the configured collection."""
        collection = self.get_collection()
        written = 0

        for record in records:
            chunk_id = record.get("chunk_id")
            if not chunk_id:
                continue

            document = {
                "chunk_id": chunk_id,
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
                {"chunk_id": chunk_id},
                {"$set": document},
                upsert=True,
            )
            written += 1

        return written

    def count_documents(self) -> int:
        """Return the number of documents in the configured collection."""
        return self.get_collection().count_documents({})

    def delete_all_documents(self) -> int:
        """Delete all documents from the configured collection."""
        result = self.get_collection().delete_many({})
        return result.deleted_count

    def vector_search(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        index_name: str | None = None,
    ) -> list[dict]:
        """Run MongoDB Atlas Vector Search against stored chunk embeddings."""
        collection = self.get_collection()
        search_index = index_name or self.config.vector_index
        results = collection.aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": search_index,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": max(top_k * 10, top_k),
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
            ]
        )
        return list(results)

    def create_vector_index(
        self,
        dimensions: int = DEFAULT_VECTOR_DIMENSIONS,
        index_name: str | None = None,
    ) -> bool:
        """Create the Atlas Vector Search index if Atlas accepts the request."""
        collection = self.ensure_collection()
        search_index = index_name or self.config.vector_index
        if self.vector_index_exists(search_index):
            return False

        try:
            collection.create_search_index(
                {
                    "name": search_index,
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": dimensions,
                                "similarity": "cosine",
                            }
                        ]
                    },
                }
            )
        except OperationFailure as error:
            message = str(error).lower()
            if "already" in message or "duplicate" in message:
                return False
            raise

        return True

    def vector_index_exists(self, index_name: str | None = None) -> bool:
        """Return whether the configured Atlas Search index already exists."""
        collection = self.get_collection()
        search_index = index_name or self.config.vector_index
        try:
            indexes = collection.list_search_indexes()
        except OperationFailure:
            return False

        return any(index.get("name") == search_index for index in indexes)


def check_env() -> dict[str, bool]:
    """Return MongoDB environment variable presence without exposing values."""
    load_dotenv()
    return {
        "MONGODB_CONNECTION_STRING": bool(os.getenv("MONGODB_CONNECTION_STRING")),
        "MONGODB_DATABASE": bool(os.getenv("MONGODB_DATABASE")),
        "MONGODB_COLLECTION": bool(os.getenv("MONGODB_COLLECTION")),
        "MONGODB_VECTOR_INDEX": bool(os.getenv("MONGODB_VECTOR_INDEX")),
    }


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Prueba segura de conexion MongoDB.")
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Muestra solo si las variables MongoDB existen o faltan.",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Ejecuta ping a MongoDB Atlas si la configuracion existe.",
    )
    parser.add_argument(
        "--create-vector-index",
        action="store_true",
        help="Crea el indice Atlas Vector Search configurado si no existe.",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Cuenta documentos en la coleccion configurada.",
    )
    return parser.parse_args()


def main() -> None:
    """Run safe MongoDB diagnostics from the command line."""
    args = parse_args()

    if args.check_env:
        for name, exists in check_env().items():
            status = "PRESENTE" if exists else "FALTA"
            print(f"{name}={status}")
        return

    if args.ping:
        try:
            MongoDBClient().ping()
        except RuntimeError as error:
            print(str(error))
        except Exception as error:
            print(f"No se pudo conectar a MongoDB Atlas. Tipo: {type(error).__name__}")
        else:
            print("Conexion MongoDB OK.")
        return

    if args.create_vector_index:
        try:
            created = MongoDBClient().create_vector_index()
        except RuntimeError as error:
            print(str(error))
        except Exception as error:
            print(f"No se pudo crear/verificar el indice vectorial. Tipo: {type(error).__name__}")
        else:
            if created:
                print("Indice vectorial solicitado en MongoDB Atlas.")
            else:
                print("Indice vectorial ya existia en MongoDB Atlas.")
        return

    if args.count:
        try:
            count = MongoDBClient().count_documents()
        except RuntimeError as error:
            print(str(error))
        except Exception as error:
            print(f"No se pudo contar documentos en MongoDB Atlas. Tipo: {type(error).__name__}")
        else:
            print(f"Documentos en MongoDB: {count}")
        return

    print(
        "Usa --check-env para validar variables, --ping para probar conexion "
        "--create-vector-index para solicitar el indice vectorial o --count "
        "para contar documentos."
    )


if __name__ == "__main__":
    main()
