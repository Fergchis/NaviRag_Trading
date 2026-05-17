from langsmith import traceable

from prompts.prompt import RAG_SYSTEM_PROMPT
from src.retrieval.retrieval import Retriever
from src.utils.llm import GitHubModelsLLM


class RAGGenerator:
    def __init__(self, system_prompt: str = RAG_SYSTEM_PROMPT):
        self.system_prompt = system_prompt
        self._retriever = None
        self.llm = GitHubModelsLLM()

    @property
    def retriever(self) -> Retriever:
        return self._get_retriever()

    @traceable(name="rag-generate")
    def generate(self, query: str, history: list[dict], top_k: int = 5) -> dict:
        chunks = self._get_retriever().retrieve(query, top_k=top_k)

        return self.generate_from_context(query=query, history=history, chunks=chunks)

    @traceable(name="rag-generate-from-context")
    def generate_from_context(self, query: str, history: list[dict], chunks: list[dict]) -> dict:
        context = "\n\n".join([chunk.get("text", "") for chunk in chunks])
        formatted_prompt = self.system_prompt.format(context=context)

        history_with_query = history + [{"role": "user", "content": query}]
        response = self.llm.generate(formatted_prompt, history_with_query)

        return {
            "answer": response["answer"],
            "sources": [chunk.get("metadata", {}) for chunk in chunks],
            "prompt_tokens": response["prompt_tokens"],
            "completion_tokens": response["completion_tokens"],
            "total_tokens": response["total_tokens"],
        }

    def _get_retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever()
        return self._retriever
