import logging

from configs.config import PathsConfig
from database.session import create_db_engine
from scripts.chunk import chunk_directory
from scripts.embed import embed_all
from scripts.index import index_directory


logger = logging.getLogger(__name__)


def create_chunks() -> bool:
    return chunk_directory(PathsConfig.RAW, PathsConfig.CHUNKS)


def create_embeddings() -> bool:
    return embed_all(PathsConfig.CHUNKS, PathsConfig.EMBEDDINGS)


def create_index() -> bool:
    engine = create_db_engine()
    try:
        return index_directory(PathsConfig.EMBEDDINGS, engine)
    finally:
        engine.dispose()


def run_pipeline() -> bool:
    stages = (
        ("chunk", create_chunks),
        ("embed", create_embeddings),
        ("index", create_index),
    )

    for name, stage in stages:
        logger.info("Stage '%s' started", name)
        if not stage():
            logger.error("Stage '%s' failed, pipeline stopped", name)
            return False
        logger.info("Stage '%s' finished", name)

    return True


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not run_pipeline():
        logger.error("Pipeline failed")
        return 1

    logger.info("Pipeline completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
