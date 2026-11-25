import re
from io import BytesIO
from pathlib import Path
from secrets import choice

from docx import Document

from .document_utils import clean_copy, load_document, text_nodes
from .links import TemporaryLinks
from .llm.ollama_provider import OllamaProvider
from .personal_data import fake_name, name_values, protected_line

CONTACT = re.compile(
    r"[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}"
    r"|(?<!\d)(?:\+?\d[ ()-]*){9,18}\d(?!\d)"
    r"|(?<!\d)\d{6,}(?!\d)"
)


def batches(texts: list[str]):
    """Делит текст по границам абзацев для локальной модели."""
    batch, size = [], 0
    for text in texts:
        if len(text) > 5000:
            raise ValueError("Абзац превышает размер контекста обезличивания.")
        if size + len(text) > 5000 or len(batch) >= 32:
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += len(text)
    if batch:
        yield batch


def substitutions(texts: list[str], model: OllamaProvider) -> dict:
    """Собирает единые замены на весь документ."""
    result = {}
    remaining = []
    for text in dict.fromkeys(texts):
        for value in name_values(text):
            if value not in result:
                result[value] = fake_name(value)
        for match in CONTACT.finditer(text):
            value = match.group()
            if value not in result:
                result[value] = fake_contact(value, len(result))
        if not protected_line(text):
            remaining.append(text)
    for batch in batches(remaining):
        for original, replacement in model.replacements(batch).items():
            if accept_proposal(original, replacement, result):
                result.setdefault(original, replacement)
    return result


def accept_proposal(original: str, replacement: str, known: dict) -> bool:
    """Проверяет границы и содержимое предложенной подстановки."""
    if protected_line(original) or replacement == "[скрыто]":
        return False
    if any(original in value or value in original for value in known):
        return False
    if ":" in original or "_" in original or "(" in original:
        return False
    return bool(re.search(r"\d|@|\b[А-ЯЁ][а-яё]+\b", original))


def fake_contact(value: str, index: int) -> str:
    """Подменяет контакт или цифровой идентификатор."""
    if "@" in value:
        return f"contact{index}@example.invalid"
    prefix = 2 if value.startswith("+7") else 0
    return value[:prefix] + "".join(
        choice("0123456789".replace(char, "")) if char.isdecimal() else char for char in value[prefix:]
    )


def replace_paragraph(nodes: list, pattern: re.Pattern, values: dict) -> None:
    """Заменяет фрагменты, в том числе разбитые на стили."""
    text = "".join(node.text or "" for node in nodes)
    matches = list(pattern.finditer(text))
    if not matches:
        return
    offsets = []
    start = 0
    for node in nodes:
        end = start + len(node.text or "")
        offsets.append((node, start, end))
        start = end
    for match in reversed(matches):
        for node, start, end in offsets:
            if end <= match.start() or start >= match.end():
                continue
            insert = values[match.group()] if start <= match.start() else ""
            content = node.text or ""
            node.text = content[:max(0, match.start() - start)] + insert + content[match.end() - start:]


def anonymize(stream: BytesIO, model: OllamaProvider) -> bytes:
    """Возвращает обезличенную текстовую копию DOCX."""
    document, roots = clean_copy(Document(stream))
    paragraphs = [text_nodes(p) for root in roots for p in root.xpath(".//w:p")]
    texts = ["".join(node.text or "" for node in nodes) for nodes in paragraphs]
    if not any(text.strip() for text in texts):
        raise ValueError("В документе нет доступного текста.")
    values = substitutions(texts, model)
    if values:
        pattern = re.compile("|".join(re.escape(key) for key in sorted(values, key=len, reverse=True)))
        for nodes in paragraphs:
            replace_paragraph(nodes, pattern, values)
    result = BytesIO()
    document.save(result)
    return result.getvalue()


class DocumentAnonymizer:
    def __init__(self, ttl_seconds: int = 300):
        """Настраивает модель и срок хранения копий."""
        self.model = OllamaProvider()
        self.links = TemporaryLinks(ttl_seconds)

    def anonymize(self, source: str | Path) -> str:
        """Принимает ссылку на DOCX и возвращает ссылку на копию."""
        with load_document(source) as stream:
            data = anonymize(stream, self.model)
        return self.links.publish(data)

    def close(self) -> None:
        """Закрывает все ссылки сервиса."""
        self.links.close()

    def __enter__(self):
        """Возвращает запущенный сервис."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Освобождает ресурсы сервиса."""
        self.close()
