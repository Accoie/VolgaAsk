from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend


class PdfConverter:
    """Конвертер PDF в Markdown без OCR"""

    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False  
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )

    def convert(self, pdf_file: Path, output_dir: Path) -> Path:
        output_file = output_dir / f"{pdf_file.stem}.md"

        result = self.converter.convert(str(pdf_file))
        markdown = result.document.export_to_markdown()
        output_file.write_text(markdown, encoding="utf-8")
        return output_file