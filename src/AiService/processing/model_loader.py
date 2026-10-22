import logging
from pathlib import Path
from typing import Callable, TypeVar

from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from ..configs.config import ModelConfig
logger = logging.getLogger(__name__)

T = TypeVar("T")

local_dir = ModelConfig.MODELS_DIR

class ModelLoader:
    
    @staticmethod
    def load_embedding_model(model_name: str) -> SentenceTransformer:
        """Загрузить модель эмбеддингов локально или скачать её при отсутствии."""
        
        return ModelLoader._load_or_download(
            local_path=ModelLoader._resolve_path(model_name),
            model_name=model_name,
            load_local_fn=lambda: SentenceTransformer(str(local_dir), local_files_only=True),
            download_fn=lambda: SentenceTransformer(model_name, local_files_only=False),
            save_fn=lambda model: model.save_pretrained(str(local_dir)),
        )


    @staticmethod
    def load_tokenizer(model_name: str, max_tokens: int) -> HuggingFaceTokenizer:
        """Загрузить токенизатор локально или скачать его при отсутствии."""
        
        tokenizer = ModelLoader._load_or_download(
            local_path=ModelLoader._resolve_path(model_name),
            model_name=model_name,
            load_local_fn=lambda: AutoTokenizer.from_pretrained(str(local_dir), local_files_only=True),
            download_fn=lambda: AutoTokenizer.from_pretrained(model_name, local_files_only=False),
            save_fn=lambda tok: tok.save_pretrained(str(local_dir)),
        )

        return HuggingFaceTokenizer(tokenizer=tokenizer, max_tokens=max_tokens)

    
    @staticmethod
    def _load_or_download(
        local_path: Path,
        model_name: str,
        load_local_fn: Callable[[], T],
        download_fn: Callable[[], T],
        save_fn: Callable[[T], None],
    ) -> T:
        try:
            result = load_local_fn()
            logger.info("Successfully loaded asset from local path: %s", local_path)
            return result
        except Exception:
            logger.warning("Asset not found at %s. Downloading '%s'...", local_path, model_name)
            
            result = download_fn()
            
            local_path.mkdir(parents=True, exist_ok=True)
            save_fn(result)
            logger.info("Successfully saved asset to local directory: %s", local_path)
            
            return result

    @staticmethod
    def _resolve_path(model_name: str) -> Path:
        return ModelConfig.MODELS_DIR / model_name.replace("/", "--")