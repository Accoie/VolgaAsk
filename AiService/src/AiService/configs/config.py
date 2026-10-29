from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class PathsConfig:
    """Все пути к данным проекта."""
    RAW = PROJECT_ROOT / "data" / "raw"
    CHUNKS = PROJECT_ROOT / "data" / "chunks"
    EMBEDDINGS = PROJECT_ROOT / "data" / "embeddings"
    MODELS = PROJECT_ROOT / "data" / "models"


class ModelsConfig:
    """Все имена моделей."""
    EMBEDDER = "deepvk/USER2-base"
    TOKENIZER = "sergeyzh/rubert-tiny-sts-v2"
    RERANKER = "sshalimov04/ru-reranker-edge-150m"
