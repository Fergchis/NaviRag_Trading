"""Controlled LLM answer generation for NaviRag Trading."""

import os

import requests
from dotenv import load_dotenv

from src.prompts import BASE_PROMPT, INSUFFICIENT_CONTEXT_MESSAGE

DEFAULT_CHAT_ENDPOINT = "https://models.github.ai/inference/chat/completions"
DEFAULT_CHAT_MODEL = "openai/gpt-4o-mini"
MAX_CONTEXT_CHARS = 8000


def load_chat_config() -> dict:
    """Load chat model configuration without exposing credentials."""
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Falta GITHUB_TOKEN en el entorno. Configura .env.")

    return {
        "token": token,
        "endpoint": os.getenv("GITHUB_CHAT_ENDPOINT", DEFAULT_CHAT_ENDPOINT),
        "model": os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODEL),
    }


def format_context(chunks: list[dict]) -> str:
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


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Build the final prompt from the question and retrieved context."""
    return BASE_PROMPT.format(
        context=format_context(chunks),
        question=question.strip(),
        insufficient_context_message=INSUFFICIENT_CONTEXT_MESSAGE,
    )


def request_chat_completion(prompt: str, token: str, endpoint: str, model: str) -> str:
    """Request a chat completion from an OpenAI-compatible endpoint."""
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 600,
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Error en proveedor de chat: HTTP {response.status_code} - "
            f"{response.text[:300]}"
        )

    payload = response.json()
    return payload["choices"][0]["message"]["content"].strip()


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Generate a controlled educational answer from retrieved chunks."""
    if not chunks or not format_context(chunks):
        return INSUFFICIENT_CONTEXT_MESSAGE

    config = load_chat_config()
    prompt = build_prompt(question=question, chunks=chunks)
    return request_chat_completion(
        prompt=prompt,
        token=config["token"],
        endpoint=config["endpoint"],
        model=config["model"],
    )


def generate_placeholder_answer(question: str, context: list[dict]) -> str:
    """Backward-compatible wrapper for older app imports."""
    return generate_answer(question=question, chunks=context)
