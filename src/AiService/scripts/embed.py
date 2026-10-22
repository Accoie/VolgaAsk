import json
import logging
from pathlib import Path
from typing import Any

from ..configs.config import EmbedderConfig
from ..processing.model_loader import ModelLoader
from ..processing.embedder import Embedder

logger = logging.getLogger(__name__)


def main() -> int:
    """Точка входа в скрипт генерации эмбеддингов для чанков."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not embed_all(EmbedderConfig.INPUT_DIR, EmbedderConfig.OUTPUT_DIR):
        logger.error("Embedding process failed")
        return 1

    logger.info("Embedding process completed successfully")
    return 0


def embed_all(input_dir: Path, output_dir: Path) -> bool:
    """Добавить эмбеддинги к каждому чанку в input_dir и сохранить в output_dir."""
    chunk_files = sorted(input_dir.glob("*.json"))
    if not chunk_files:
        logger.error("No JSON files found in directory %s", input_dir)
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    embedding_model = ModelLoader.load_embedding_model(EmbedderConfig.EMBEDDER_NAME)
    embedder = Embedder(embedding_model)

    failed = False
    for chunk_file in chunk_files:
        try:
            chunks = process_and_embed_file(chunk_file, embedder)
            save_embedded_chunks(chunks, chunk_file, output_dir)
            logger.info("Successfully embedded and saved %s", chunk_file.name)
        except Exception:
            logger.exception("Failed to process file %s", chunk_file.name)
            failed = True

    return not failed


def process_and_embed_file(chunk_file: Path, embedder: Embedder) -> list[dict[str, Any]]:
    """Прочитать чанки из файла, сгенерировать эмбеддинги и добавить их в метаданные."""
    chunks: list[dict[str, Any]] = json.loads(chunk_file.read_text(encoding="utf-8"))
    
    texts = [chunk["text"] for chunk in chunks]
    vectors = embedder.embed_batch(texts)
    
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
        
    return chunks


def save_embedded_chunks(chunks: list[dict[str, Any]], chunk_file: Path, output_dir: Path) -> Path:
    """Сохранить обогащенные эмбеддингами чанки обратно в JSON-файл."""
    output_file = output_dir / chunk_file.name
    output_file.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_file


if __name__ == "__main__":
    raise SystemExit(main())
