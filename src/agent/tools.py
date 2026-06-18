from langchain_core.tools import tool

from src.retrieval.retrieval import Retriever


_retriever: Retriever | None = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


@tool(response_format="content_and_artifact")
def rag_search(query: str, top_k: int = 5) -> tuple[str, dict]:
    """Busca contexto educativo de trading en la base documental del proyecto."""
    chunks = _get_retriever().retrieve(query=query, top_k=top_k)
    sources = [chunk.get("metadata", {}) for chunk in chunks]
    artifact = {
        "sources": sources,
        "chunk_count": len(chunks),
    }

    if not chunks:
        return "No se encontro informacion relevante en los documentos.", artifact

    context = "\n\n".join(chunk.get("text", "") for chunk in chunks)
    return context, artifact


tools = [rag_search]
