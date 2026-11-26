from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from .word import WordForm


def convert_pdf(content):
    """Готовит редактируемую копию PDF-бланка."""
    from pdf2docx import Converter

    with TemporaryDirectory(prefix="volga-form-") as directory:
        source = Path(directory) / "source.pdf"
        target = Path(directory) / "form.docx"
        source.write_bytes(content)
        try:
            with closing(Converter(str(source))) as converter:
                converter.convert(str(target), ignore_page_error=False)
            result = target.read_bytes()
        except Exception as error:
            raise ValueError("Не удалось преобразовать PDF-бланк в DOCX.") from error
    if not any(block["text"].strip() for block in WordForm(result).blocks()):
        raise ValueError("В PDF нет редактируемого текста.")
    return result
