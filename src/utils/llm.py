import os

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_chat_model() -> ChatOpenAI:
    """Build a LangChain chat model against the GitHub Models endpoint."""
    endpoint = os.getenv(
        "GITHUB_MODELS_CHAT_ENDPOINT",
        "https://models.github.ai/inference/chat/completions",
    )
    base_url = endpoint.removesuffix("/chat/completions").rstrip("/")
    return ChatOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url=base_url,
        model=os.getenv("GITHUB_CHAT_MODEL", "openai/gpt-4o-mini"),
        temperature=0,
    )


class GitHubModelsLLM:
    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.model = os.getenv("GITHUB_CHAT_MODEL", model)
        self.token = os.getenv("GITHUB_TOKEN")
        self.endpoint = "https://models.github.ai/inference/chat/completions"

    def generate(self, system_prompt: str, history: list[dict]) -> dict:
        messages = [{"role": "system", "content": system_prompt}] + history
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
            },
            timeout=60,
        )
        response.raise_for_status()

        payload = response.json()
        usage = payload.get("usage", {})
        return {
            "answer": payload["choices"][0]["message"]["content"],
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
