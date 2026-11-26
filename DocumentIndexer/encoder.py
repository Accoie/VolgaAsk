from sentence_transformers import SentenceTransformer

from settings import PathsConfig


def load_model(model_name, load, save):
    """Открывает модель из каталога индексатора или скачивает её."""
    path = PathsConfig.MODELS / model_name.replace("/", "--")
    try:
        return load(str(path), local_files_only=True)
    except OSError:
        model = load(model_name)
        path.mkdir(parents=True, exist_ok=True)
        save(model, str(path))
        return model


def load_embedding_model(model_name):
    """Загружает модель, совместимую с поисковым индексом."""
    return load_model(model_name, SentenceTransformer, SentenceTransformer.save_pretrained)


class Embedder:
    def __init__(self, model: SentenceTransformer) -> None:
        self.model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Кодирует фрагменты для поиска по документам."""
        vectors = self.model.encode(texts, prompt_name="search_document")
        return vectors.tolist()
