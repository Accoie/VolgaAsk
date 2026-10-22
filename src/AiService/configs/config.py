import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConverterConfig:
    INPUT_DIR = PROJECT_ROOT / "data" / "raw"

class ChunkerConfig:
    OUTPUT_DIR = PROJECT_ROOT / "data" / "chunks"
    TOKENIZER_NAME = "sergeyzh/rubert-tiny-sts-v2"

class ModelConfig:
    MODELS_DIR = PROJECT_ROOT / "data" / "models"

class EmbedderConfig:
    EMBEDDER_NAME = "sergeyzh/rubert-tiny-sts-v2"
    INPUT_DIR = PROJECT_ROOT / "data" / "chunks"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "embeddings"

class DatabaseConfig:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ai_service:secret@localhost:5432/ai_service",
    )