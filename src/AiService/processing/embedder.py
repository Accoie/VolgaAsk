from pathlib import Path

from sentence_transformers import SentenceTransformer

from .model_loader import ModelLoader
from ..configs.config import EmbedderConfig

class Embedder:

    def __init__(self, model: SentenceTransformer) -> None:
        self.model: SentenceTransformer = model


    @classmethod
    def create_from_path(
        cls
    ) -> "Embedder":
        model = ModelLoader.load_embedding_model(EmbedderConfig.EMBEDDER_NAME)
        return cls(model)


    def embed_text(self, text: str) -> list[float]:
        return [float(v) for v in self.model.encode(text)]


    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts)
        return [[float(v) for v in vec] for vec in vectors]