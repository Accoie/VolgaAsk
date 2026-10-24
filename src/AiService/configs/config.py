import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class PathsConfig:
    """Все пути к данным проекта."""
    RAW = PROJECT_ROOT / "data" / "raw"
    CHUNKS = PROJECT_ROOT / "data" / "chunks"
    EMBEDDINGS = PROJECT_ROOT / "data" / "embeddings"
    MODELS = PROJECT_ROOT / "data" / "models"


class ModelsConfig:
    """Все имена моделей."""
    EMBEDDER = "sergeyzh/rubert-tiny-sts-v2"
    TOKENIZER = "sergeyzh/rubert-tiny-sts-v2"
    RERANKER = "sshalimov04/ru-reranker-edge-150m"


class DatabaseConfig:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ai_service:secret@localhost:5432/ai_service",
    )