import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class PathsConfig:
    """Пути к моделям и корпусу индексатора."""

    RAW = Path(os.getenv("KB_ROOT", ROOT.parent / "storage" / "kb")) / "bootstrap"
    CHUNKS = ROOT / "data" / "chunks"
    EMBEDDINGS = ROOT / "data" / "embeddings"
    MODELS = Path(os.getenv("INDEXER_MODELS_DIR", ROOT / "data" / "models"))


class ModelsConfig:
    """Модели разбиения текста и записи в поисковый индекс."""

    EMBEDDER = "deepvk/USER2-base"
    TOKENIZER = "sergeyzh/rubert-tiny-sts-v2"
