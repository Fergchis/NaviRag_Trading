import os

import requests
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

load_dotenv()


class GitHubModelsEmbeddings(Embeddings):
    def __init__(self, model: str = "openai/text-embedding-3-small"):
        self.model = os.getenv("GITHUB_EMBEDDING_MODEL", model)
        self.token = os.getenv("GITHUB_TOKEN")
        self.endpoint = os.getenv(
            "GITHUB_MODELS_EMBEDDINGS_ENDPOINT",
            "https://models.github.ai/inference/embeddings",
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item.get("index", 0))
        return [item["embedding"] for item in data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def get_embedding(self, text: str) -> list[float]:
        return self.embed_query(text)
