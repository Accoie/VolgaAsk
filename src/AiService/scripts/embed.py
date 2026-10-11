import json
import logging
from pathlib import Path

from ..configs.config import EmbeddingConfig
from ..processing.embedder import Embedder


logger = logging.getLogger(__name__)


def embed_all(input_dir: Path, output_dir: Path) -> bool:
    """Добавить эмбеддинги к каждому чанку в input_dir и сохранить в output_dir."""
    chunk_files: list[Path] = sorted(input_dir.glob("*.json"))
    if not chunk_files:
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    embedder = Embedder.create_from_path(
        str(EmbeddingConfig.MODEL_PATH),
        EmbeddingConfig.MODEL_NAME,
    )

    failed = False
    for chunk_file in chunk_files:
        try:
            chunks: list[dict] = json.loads(chunk_file.read_text(encoding="utf-8"))
            vectors = embedder.embed_batch([chunk["text"] for chunk in chunks])
            for chunk, vector in zip(chunks, vectors):
                chunk["embedding"] = vector

            output_file: Path = output_dir / chunk_file.name
            output_file.write_text(
                json.dumps(chunks, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Embedded %s", chunk_file.name)
        except Exception as error:
            logger.error("%s: %s", chunk_file.name, error)
            failed = True

    return not failed


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    success = embed_all(EmbeddingConfig.INPUT_DIR, EmbeddingConfig.OUTPUT_DIR)
    if not success:
        logger.error("Embedding failed")
        return 1

    logger.info("Embedding complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())