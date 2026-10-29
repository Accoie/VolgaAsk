from pathlib import Path

from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model: SentenceTransformer) -> None:
        self.model = model

    def embed_text(self, text: str) -> list[float]:
        return [float(v) for v in self.model.encode(text, prompt_name="search_query")]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, prompt_name="search_document")
        return [[float(v) for v in vec] for vec in vectors]