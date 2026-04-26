"""Controlled RAG answer generation for NaviRag Trading."""

from prompts.prompt import BASE_PROMPT, INSUFFICIENT_CONTEXT_MESSAGE
from src.utils.llm import GitHubModelsLLM

MAX_CONTEXT_CHARS = 8000


class RAGGenerator:
    """Generate controlled educational answers from retrieved chunks."""

    def __init__(
        self,
        llm: GitHubModelsLLM | None = None,
        system_prompt: str = BASE_PROMPT,
    ) -> None:
        self.llm = llm
        self.system_prompt = system_prompt

    def format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks with traceable source metadata."""
        formatted_chunks = []
        remaining_chars = MAX_CONTEXT_CHARS

        for index, chunk in enumerate(chunks, start=1):
            text = (chunk.get("text") or "").strip()
            if not text:
                continue

            source = (
                f"Fuente {index}: archivo={chunk.get('file')}, "
                f"pagina={chunk.get('page')}, chunk_id={chunk.get('chunk_id')}"
            )
            available_text_chars = remaining_chars - len(source) - 2
            if available_text_chars <= 0:
                break

            clipped_text = text[:available_text_chars]
            formatted_chunks.append(f"{source}\n{clipped_text}")
            remaining_chars -= len(source) + len(clipped_text) + 2

        return "\n\n".join(formatted_chunks)

    def build_prompt(self, question: str, chunks: list[dict]) -> str:
        """Build the final prompt from the question and retrieved context."""
        return self.system_prompt.format(
            context=self.format_context(chunks),
            question=question.strip(),
            insufficient_context_message=INSUFFICIENT_CONTEXT_MESSAGE,
        )

    def generate(self, question: str, chunks: list[dict]) -> dict:
        """Generate an answer and include source chunks and token usage."""
        if not chunks or not self.format_context(chunks):
            return {
                "answer": INSUFFICIENT_CONTEXT_MESSAGE,
                "sources": chunks,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        prompt = self.build_prompt(question=question, chunks=chunks)
        llm = self.llm or GitHubModelsLLM()
        response = llm.generate(
            system_prompt="",
            history=[{"role": "user", "content": prompt}],
        )
        return {
            "answer": response["answer"],
            "sources": chunks,
            "prompt_tokens": response["prompt_tokens"],
            "completion_tokens": response["completion_tokens"],
            "total_tokens": response["total_tokens"],
        }


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Generate an answer string using the RAG generator."""
    return RAGGenerator().generate(question=question, chunks=chunks)["answer"]
