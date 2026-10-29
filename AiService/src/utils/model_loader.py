import logging
from pathlib import Path
from typing import Callable, TypeVar

from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import AutoTokenizer

from configs.config import PathsConfig


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ModelLoader:

    @staticmethod
    def load_embedding_model(model_name: str) -> SentenceTransformer:
        """Загрузить модель эмбеддингов локально или скачать её при отсутствии."""
        local_path = ModelLoader._resolve_path(model_name)
        return ModelLoader._load_or_download(
            local_path=local_path,
            model_name=model_name,
            load_local_fn=lambda: SentenceTransformer(str(local_path), local_files_only=True),
            download_fn=lambda: SentenceTransformer(model_name, local_files_only=False),
            save_fn=lambda model: model.save_pretrained(str(local_path)),
        )

    @staticmethod
    def load_tokenizer(model_name: str, max_tokens: int) -> HuggingFaceTokenizer:
        """Загрузить токенизатор локально или скачать его при отсутствии."""
        local_path = ModelLoader._resolve_path(model_name)
        tokenizer = ModelLoader._load_or_download(
            local_path=local_path,
            model_name=model_name,
            load_local_fn=lambda: AutoTokenizer.from_pretrained(str(local_path), local_files_only=True),
            download_fn=lambda: AutoTokenizer.from_pretrained(model_name, local_files_only=False),
            save_fn=lambda tok: tok.save_pretrained(str(local_path)),
        )
        return HuggingFaceTokenizer(tokenizer=tokenizer, max_tokens=max_tokens)

    @staticmethod
    def load_cross_encoder(model_name: str) -> CrossEncoder:
        """Загрузить CrossEncoder локально или скачать при отсутствии."""
        local_path = ModelLoader._resolve_path(model_name)
        return ModelLoader._load_or_download(
            local_path=local_path,
            model_name=model_name,
            load_local_fn=lambda: CrossEncoder(str(local_path), local_files_only=True),
            download_fn=lambda: CrossEncoder(model_name, local_files_only=False),
            save_fn=lambda model: model.save(str(local_path)),
        )

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
            logger.info("Loaded from %s", local_path)
            return result
        except OSError:
            logger.warning("Not found at %s. Downloading '%s'...", local_path, model_name)

        result = download_fn()
        local_path.mkdir(parents=True, exist_ok=True)
        save_fn(result)
        logger.info("Saved to %s", local_path)
        return result

    @staticmethod
    def _resolve_path(model_name: str) -> Path:
        return PathsConfig.MODELS / model_name.replace("/", "--")