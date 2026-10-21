import os
from pathlib import Path


class ConverterConfig:
    """Конфигурация конвертера."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    INPUT_DIR = PROJECT_ROOT / "data" / "raw"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

class ChunkerConfig:
    """Конфигурация чанкера."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    INPUT_DIR = PROJECT_ROOT / "data" / "processed"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "chunks"

class ModelConfig:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    MODEL_NAME = "sergeyzh/rubert-tiny-sts-v2"
    MODEL_PATH = PROJECT_ROOT / "data" / "models" / "rubert-tiny-sts-v2"
    INPUT_DIR = PROJECT_ROOT / "data" / "chunks"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "embeddings"


class DatabaseConfig:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ai_service:secret@localhost:5432/ai_service",
    )