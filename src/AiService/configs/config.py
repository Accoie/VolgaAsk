from pathlib import Path


class ConverterConfig:
    """Конфигурация конвертера."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    INPUT_DIR = PROJECT_ROOT / "data" / "raw"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"