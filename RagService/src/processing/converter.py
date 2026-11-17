import logging
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument

logger = logging.getLogger(__name__)


class Converter:
    """Конвертирует PDF документы в DoclingDocument."""

    SUPPORTED_EXTENSIONS = frozenset([".pdf"])


    def __init__(self) -> None:
        """Инициализирует конвертер с настройками конвейера для PDF."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False
        pipeline_options.force_backend_text = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )


    def convert(self, file_path: Path) -> DoclingDocument:
        """Конвертирует PDF-файл в формат DoclingDocument."""
        if file_path.suffix.casefold() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: '{file_path.name}'. "
                f"Allowed extensions: {list(self.SUPPORTED_EXTENSIONS)}"
            )

        logger.info("Converting %s", file_path.name)
        return self.converter.convert(str(file_path)).document
