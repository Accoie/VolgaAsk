import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class Embedder:
    
    def __init__(self, model: SentenceTransformer) -> None:
        self.model: SentenceTransformer = model

    @classmethod
    def create_from_path(
        cls,
        local_path: str,
        hf_name: str,
    ) -> "Embedder":
        """
        Создаёт Embedder, загружая модель из local_path.
        Если модели нет, то скачивает из HuggingFace репозитория с именем hf_name.
        """
        try:
            model = SentenceTransformer(local_path, local_files_only=True)
            logger.info("Эмбеддер загружен из %s.", local_path)
        except Exception:
            logger.warning(
                "Модель не найдена в %s. Скачивание '%s'",
                local_path, hf_name,
            )
            model = SentenceTransformer(hf_name, local_files_only=False)
            model.save_pretrained(local_path)
            logger.info("Модель сохранена в %s.", local_path)

        return cls(model)

    def embed_text(self, text: str) -> list[float]:
        return [float(v) for v in self.model.encode(text)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts)
        return [[float(v) for v in vec] for vec in vectors]