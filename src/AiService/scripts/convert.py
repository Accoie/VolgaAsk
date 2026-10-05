import logging
import sys
from pathlib import Path

if __package__:
    from ..configs.config import ConverterConfig
    from ..core.converter import PdfConverter
else:
    project_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_dir))
    from configs.config import ConverterConfig
    from core.converter import PdfConverter

logger = logging.getLogger(__name__)


def convert_pdf_directory(input_dir: Path, output_dir: Path) -> bool:
    """
    Пакетная конвертация директории.
    Возвращает True, если все файлы успешно обработаны.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    pdf_files = sorted(input_path.glob("*.pdf"))

    if not pdf_files:
        logger.error("No PDF files found in %s", input_path)
        return False

    output_path.mkdir(parents=True, exist_ok=True)
    converter = PdfConverter()
    failed = False

    for pdf_file in pdf_files:
        try:
            converter.convert(pdf_file, output_path)
        except Exception as error:
            logger.error("%s: %s", pdf_file.name, error)
            failed = True

    return not failed


def main() -> int:
    logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    return 0 if convert_pdf_directory(
        ConverterConfig.INPUT_DIR,
        ConverterConfig.OUTPUT_DIR,
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
