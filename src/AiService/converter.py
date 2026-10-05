from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

class PdfConvertError(Exception):
    """Базовая ошибка конвертации PDF."""


class CorruptedPdfError(PdfConvertError):
    """PDF повреждён или не читается."""


class PdfConverter:
    """Конвертер PDF в Markdown."""

    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(backend=PyPdfiumDocumentBackend)
            }
        )

    def convert_all(self) -> None:
        pdf_files = sorted(self.input_dir.glob("*.pdf"))
        if not pdf_files:
            raise PdfConvertError(f"No PDF files found in {self.input_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        for pdf_file in pdf_files:
            self.convert(pdf_file)

    def convert(self, pdf_file: Path) -> Path:
        """
        Конвертировать один PDF.

        Возвращает путь к Markdown.
        Бросает CorruptedPdfError, если PDF не читается.
        """

        output_file = self.output_dir / f"{pdf_file.stem}.md"

        try:
            result = self.converter.convert(str(pdf_file))
            markdown = result.document.export_to_markdown()
        except Exception as error:
            raise CorruptedPdfError(f"{pdf_file.name}: {error}") from error

        output_file.write_text(markdown, encoding="utf-8")
        print(f"[OK] {pdf_file.name} -> {output_file}")
        return output_file