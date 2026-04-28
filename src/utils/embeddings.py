import os

import requests
from dotenv import load_dotenv

load_dotenv()


class EmbeddingClient:
    def __init__(self, model: str = "openai/text-embedding-3-small"):
        self.model = os.getenv("GITHUB_EMBEDDING_MODEL", model)
        self.token = os.getenv("GITHUB_TOKEN")
        self.endpoint = os.getenv(
            "GITHUB_MODELS_EMBEDDINGS_ENDPOINT",
            "https://models.github.ai/inference/embeddings",
        )

    def get_embedding(self, text: str) -> list[float]:
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": text,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
