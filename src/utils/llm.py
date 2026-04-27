"""GitHub Models chat client for NaviRag Trading."""

import os

import requests
from dotenv import load_dotenv

DEFAULT_GITHUB_CHAT_MODEL = "openai/gpt-4o-mini"
DEFAULT_GITHUB_CHAT_ENDPOINT = "https://models.github.ai/inference/chat/completions"


class GitHubModelsLLM:
    """GitHub Models chat completion client."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("GITHUB_TOKEN")
        if not self.api_key:
            raise RuntimeError("Falta GITHUB_TOKEN en el entorno. Configura .env.")

        self.model = model or os.getenv("GITHUB_CHAT_MODEL") or DEFAULT_GITHUB_CHAT_MODEL
        self.endpoint = (
            endpoint
            or os.getenv("GITHUB_MODELS_CHAT_ENDPOINT")
            or DEFAULT_GITHUB_CHAT_ENDPOINT
        )

    def generate(self, system_prompt: str, history: list[dict]) -> dict:
        """Generate a chat response and return answer plus token usage."""
        messages = history
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + history

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 600,
            },
            timeout=60,
        )

        if not response.ok:
            raise RuntimeError(
                f"Error en GitHub Models chat: HTTP {response.status_code} - "
                f"{response.text[:300]}"
            )

        payload = response.json()
        usage = payload.get("usage", {})
        return {
            "answer": payload["choices"][0]["message"]["content"].strip(),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
