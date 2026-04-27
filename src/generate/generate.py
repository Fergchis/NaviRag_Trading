from prompts.prompt import BASE_PROMPT, INSUFFICIENT_CONTEXT_MESSAGE
from src.retrieval.retrieval import Retriever
from src.utils.llm import GitHubModelsLLM


class RAGGenerator:
    def __init__(self, system_prompt: str = BASE_PROMPT):
        self.system_prompt = system_prompt
        self.retriever = Retriever()
        self.llm = GitHubModelsLLM()

    def generate(self, query: str, history: list[dict], top_k: int = 5) -> dict:
        chunks = self.retriever.retrieve(query, top_k=top_k)

        context = "\n\n".join([chunk["text"] for chunk in chunks if chunk.get("text")])
        formatted_prompt = self.system_prompt.format(
            context=context,
            question=query,
            insufficient_context_message=INSUFFICIENT_CONTEXT_MESSAGE,
        )

        history_with_query = history + [{"role": "user", "content": query}]
        response = self.llm.generate(formatted_prompt, history_with_query)

        return {
            "answer": response["answer"],
            "sources": chunks,
            "prompt_tokens": response["prompt_tokens"],
            "completion_tokens": response["completion_tokens"],
            "total_tokens": response["total_tokens"],
        }
