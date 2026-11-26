from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PathsConfig:
    """Все пути к данным проекта."""
    MODELS = PROJECT_ROOT / "data" / "models"


class ModelsConfig:
    """Все имена моделей."""
    EMBEDDER = "deepvk/USER2-base"
    RERANKER = "sshalimov04/ru-reranker-edge-150m"
