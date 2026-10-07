import logging

from ..core.chunker import Chunker
from ..configs.config import ChunkerConfig


logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    chunker = Chunker()
    success = chunker.chunk_all(
        input_dir=ChunkerConfig.INPUT_DIR,
        output_dir=ChunkerConfig.OUTPUT_DIR,
    )

    if not success:
        logger.error("Chunking failed")
        return 1

    logger.info("Chunking complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())