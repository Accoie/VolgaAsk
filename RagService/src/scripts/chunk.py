import json
import logging
from pathlib import Path
from typing import Any

from configs.config import ModelsConfig, PathsConfig
from processing.chunker import Chunker
from processing.converter import Converter
from utils.date_parser import DateParser

logger = logging.getLogger(__name__)

MAX_TOKENS = 256

def main() -> int:
    """Точка входа в скрипт разбиения документов на чанки."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not chunk_directory(PathsConfig.RAW, PathsConfig.CHUNKS):
        logger.error("Chunking process failed")
        return 1

    logger.info("Chunking process completed successfully")
    return 0


def chunk_directory(input_dir: Path, output_dir: Path) -> bool:
    """Собрать, обработать и сохранить все файлы из директории."""

    input_files = sorted(filter(Path.is_file, input_dir.iterdir()))
    if not input_files:
        logger.error("Directory %s is empty or contains no files", input_dir)
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    converter = Converter()
    chunker = Chunker(ModelsConfig.TOKENIZER, MAX_TOKENS)

    failed = False
    for input_file in input_files:
        try:
            chunks = chunk_file(input_file, converter, chunker)
            output_file = save_chunks(chunks, input_file, output_dir)
            logger.info("Successfully saved %d chunks to file %s", len(chunks), output_file.name)
        except Exception:
            logger.exception("Failed to process file %s", input_file.name)
            failed = True

    return not failed


def chunk_file(
    input_file: Path, 
    converter: Converter, 
    chunker: Chunker
) -> list[dict[str, Any]]:
    """Сконвертировать файл в документ, разбить на чанки и обогатить их датой."""
    doc = converter.convert(input_file)
    chunks = chunker.chunk(doc, input_file.stem)
    
    document_date = DateParser.parse_data_from_text(input_file.name)
    for chunk in chunks:
        chunk["document_date"] = document_date
        
    return chunks


def save_chunks(chunks: list[dict[str, Any]], input_file: Path, output_dir: Path) -> Path:
    """Сохранить полученные чанки в JSON-файл с корректным именем."""
    output_name = (
        f"{input_file.stem}.json"
        if input_file.suffix.casefold() == ".pdf"
        else f"{input_file.name}.json"
    )
    output_file = output_dir / output_name
    
    output_file.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_file


if __name__ == "__main__":
    raise SystemExit(main())
