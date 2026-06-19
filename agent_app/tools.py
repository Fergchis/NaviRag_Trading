import os
import uuid
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langsmith import traceable
from pymongo import MongoClient

from agent_app.utils.embeddings import GitHubModelsEmbeddings

load_dotenv()

embedder = GitHubModelsEmbeddings()
mongo_client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING"))
collection = mongo_client[
    os.getenv("MONGODB_DATABASE", "navirag")
][os.getenv("MONGODB_COLLECTION", "embeddings")]
MEMORY_NAMESPACE = "agent_memories"


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


@tool
def save_memory(
    memory: str,
    config: RunnableConfig,
    store: Annotated[BaseStore, InjectedStore()],
) -> str:
    """Guarda información útil y estable del usuario en la memoria long-term."""
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "No se pudo guardar la memoria porque falta user_id."

    memory_id = str(uuid.uuid4())
    store.put(
        (MEMORY_NAMESPACE, str(user_id)),
        memory_id,
        {"memory": memory},
    )
    return f"Memoria guardada correctamente con id {memory_id}."


@tool
def search_memory(
    query: str,
    config: RunnableConfig,
    store: Annotated[BaseStore, InjectedStore()],
) -> str:
    """Busca información del usuario en la memoria long-term."""
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "No se pudo consultar la memoria porque falta user_id."

    results = store.search(
        (MEMORY_NAMESPACE, str(user_id)),
        query=query,
        limit=5,
    )
    memories = [
        str(item.value.get("memory"))
        for item in results
        if isinstance(item.value, dict) and item.value.get("memory")
    ]
    if not memories:
        return "No se encontraron memorias relevantes para esta consulta."
    return "Memorias encontradas:\n- " + "\n- ".join(memories)


rag_tools = [rag_search]
memory_tools = [save_memory, search_memory]
