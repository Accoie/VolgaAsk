from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.pipeline_options import PdfPipelineOptions

class PdfConverter:
    """Конвертер PDF в Markdown без ocr"""

    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True  
    
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(backend=PyPdfiumDocumentBackend)
            }
        )

    def convert(self, pdf_file: Path, output_dir: Path) -> Path:
        """
        Конвертировать один PDF.
        Возвращает путь к Markdown.
        """
        output_file = output_dir / f"{pdf_file.stem}.md"

        result = self.converter.convert(str(pdf_file))
        markdown = result.document.export_to_markdown()
        output_file.write_text(markdown, encoding="utf-8")
        return output_file
