from io import BytesIO
import re

from docx import Document

from document_review.anonymizer import anonymize
from document_review.llm.ollama_provider import OllamaProvider
from document_review.anonymization_checker import AnonymizationChecker


def test_local_anonymization_and_check():
    """Проверяет замену персональных данных и независимый ответ Qwen."""
    source = Document()
    source.add_paragraph("Контактный телефон: +7 (900) 123-45-67")
    source.add_paragraph("Ф.И.О. (полностью) Петров Никита Павлович")
    captions = ["ИНН ", "(контактный телефон)", "Дата 23.11.2026___________", "(подпись)(расшифровка подписи)"]
    for caption in captions:
        source.add_paragraph(caption)
    source.add_table(1, 1).cell(0, 0).text = "ИНН: 123456789012"
    stream = BytesIO()
    source.save(stream)
    original = stream.getvalue()
    stream.seek(0)
    model = OllamaProvider()
    copy = anonymize(stream, model)
    result = Document(BytesIO(copy))
    assert result.paragraphs[0].text.startswith("Контактный телефон: ")
    assert result.tables[0].cell(0, 0).text.startswith("ИНН: ")
    phone = result.paragraphs[0].text.removeprefix("Контактный телефон: ")
    inn = result.tables[0].cell(0, 0).text.removeprefix("ИНН: ")
    assert phone.strip() and "79001234567" not in "".join(char for char in phone if char.isdigit())
    assert re.fullmatch(r"\d{12}", inn) and inn != "123456789012"
    name = result.paragraphs[1].text
    assert re.fullmatch(r"Ф\.И\.О\. \(полностью\) [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+", name)
    assert not {"Петров", "Никита", "Павлович"}.intersection(name.split())
    assert [p.text for p in result.paragraphs[2:]] == captions
    checker = AnonymizationChecker(model)
    assert checker.check(original, copy).safe
    result.tables[0].cell(0, 0).text = "ИНН: 123456789012"
    leaked = BytesIO()
    result.save(leaked)
    assert not checker.check(original, leaked.getvalue()).safe
