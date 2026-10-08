import logging
from pathlib import Path

from ..core.chunker import Chunker
from ..configs.config import ChunkerConfig


logger = logging.getLogger(__name__)


def chunk_all(input_dir: Path, output_dir: Path) -> bool:
    """Обработать все .md из input_dir в output_dir файлами в формате json."""
    md_files: list[Path] = sorted(input_dir.glob("*.md"))
    if not md_files:
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    chunker = Chunker()
    failed: bool = False

    for md_file in md_files:
        try:
            chunker.chunk(md_file, output_dir)
            logger.info("Chunked %s", md_file.name)
        except Exception as error:
            logger.error("%s: %s", md_file.name, error)
            failed = True

    return not failed


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    success = chunk_all(
        ChunkerConfig.INPUT_DIR,
        ChunkerConfig.OUTPUT_DIR,
    )

    if not success:
        logger.error("Chunking failed")
        return 1

    logger.info("Chunking complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())