"""Real OpenRouter embeddings using its OpenAI-compatible API."""
import os
from openai import OpenAI
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """OpenRouter adapter; vector dimension is learned from the actual response."""

    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        self.model_name = model_name
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is missing")
        self.client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        self.dimensions = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        vectors = [item.embedding for item in response.data]
        self._validate(vectors, len(texts))
        return vectors

    def embed_query(self, question: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model_name, input=[question])
        vector = response.data[0].embedding
        self._validate([vector], 1)
        return vector

    def _validate(self, vectors: list[list[float]], expected: int) -> None:
        if len(vectors) != expected or not vectors or not vectors[0]:
            raise RuntimeError("Embedding provider returned an invalid vector response")
        dimensions = len(vectors[0])
        if any(len(v) != dimensions for v in vectors):
            raise RuntimeError("Embedding vectors have inconsistent dimensions")
        if self.dimensions not in (0, dimensions):
            raise RuntimeError("Embedding dimension changed during this run")
        self.dimensions = dimensions
