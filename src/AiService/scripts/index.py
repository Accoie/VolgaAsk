import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..configs.config import DatabaseConfig, EmbedderConfig
from ..database.indexer import Indexer


logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    engine = create_engine(DatabaseConfig.DATABASE_URL)
    try:
        return 0 if index_directory(EmbedderConfig.OUTPUT_DIR, engine) else 1
    finally:
        engine.dispose()


def index_directory(input_dir: Path, engine: Engine) -> bool:
    chunk_files = get_chunk_files(input_dir)
    if not chunk_files:
        return False

    indexer = initialize_indexer(engine)
    if not indexer:
        return False

    return process_chunk_files(indexer, chunk_files)


def get_chunk_files(input_dir: Path) -> list[Path]:
    chunk_files: list[Path] = sorted(input_dir.glob("*.json"))
    if not chunk_files:
        logger.error("No embedding files found in %s", input_dir)
    return chunk_files


def initialize_indexer(engine: Engine) -> Indexer | None:
    indexer = Indexer(engine)
    try:
        indexer.ensure_schema()
        return indexer
    except Exception as error:
        logger.error("Failed to create database schema: %s", error)
        return None


def process_chunk_files(indexer: Indexer, chunk_files: list[Path]) -> bool:
    failed = False
    for chunk_file in chunk_files:
        try:
            count = indexer.load_file(chunk_file)
            logger.info("Indexed %s chunks from %s", count, chunk_file.name)
        except Exception as error:
            logger.error("%s: %s", chunk_file.name, error)
            failed = True
    return not failed


if __name__ == "__main__":
    raise SystemExit(main())
