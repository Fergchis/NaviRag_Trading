import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langsmith import traceable
from pymongo import MongoClient

from agent_app.utils.embeddings import GitHubModelsEmbeddings

load_dotenv()

embedder = GitHubModelsEmbeddings()
mongo_client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
collection = mongo_client[
    os.getenv("MONGODB_DATABASE", "navirag")
][os.getenv("MONGODB_COLLECTION", "embeddings")]


@traceable(name="retrieve")
def retrieve(query: str, top_k: int = 5) -> list[dict]:
    query_embedding = embedder.embed_query(query)
    index_name = os.getenv("MONGODB_VECTOR_INDEX", "vector_index")
    results = collection.aggregate([
        {
            "$vectorSearch": {
                "index": index_name,
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


def format_retrieved_documents(documents: list[dict]) -> str:
    blocks = []
    for index, document in enumerate(documents, start=1):
        metadata = document.get("metadata", {})
        filename = metadata.get("filename") or metadata.get("file") or "-"
        source = metadata.get("source") or filename
        chunk_id = document.get("chunk_id", "-")
        score = document.get("score")
        score_text = f"{score:.6f}" if isinstance(score, (int, float)) else "-"
        fragment = document.get("text", "")
        blocks.append(
            f"[FUENTE {index}]\n"
            f"filename: {filename}\n"
            f"source: {source}\n"
            f"chunk_id: {chunk_id}\n"
            f"score: {score_text}\n\n"
            f"fragmento:\n{fragment}"
        )
    return "\n\n".join(blocks)


@tool
def rag_search(query: str) -> str:
    """Busca fragmentos y fuentes en la base documental educativa de trading."""
    documents = retrieve(query)
    if not documents:
        return "No se encontró información relevante en los documentos."
    return format_retrieved_documents(documents)


rag_tools = [rag_search]
