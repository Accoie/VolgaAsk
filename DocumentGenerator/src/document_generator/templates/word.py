import re
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from lxml import etree
from pydantic import BaseModel, Field

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SPACE = "{http://www.w3.org/XML/1998/namespace}space"
MARKER = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")
PART = re.compile(r"word/(document|header\d+|footer\d+)\.xml")
SPECIAL = {W + "tab": "\t", W + "br": "\n", W + "cr": "\n"}


class Edit(BaseModel):
    paragraph: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    component: str | None = None
    text: str = Field(default="", max_length=4000)


def tokens(paragraph):
    """Читает текстовые узлы абзаца в порядке документа."""
    for node in paragraph.iter():
        if node.tag not in SPECIAL and node.tag != W + "t":
            continue
        if next(node.iterancestors(W + "p")) is paragraph:
            yield node, SPECIAL.get(node.tag, node.text or "")


def replace_range(paragraph, start, end, value):
    """Заменяет диапазон с сохранением оформления соседних фрагментов."""
    nodes = list(tokens(paragraph))
    if not 0 <= start <= end <= sum(len(text) for _, text in nodes):
        raise ValueError("Выделите текст внутри одного абзаца.")
    offset = 0
    inserted = False
    for node, text in nodes:
        left, right = offset, offset + len(text)
        offset = right
        if right <= start or left >= end:
            continue
        before = text[:max(0, start - left)]
        after = text[max(0, end - left):]
        node.tag = W + "t"
        node.text = before + ("" if inserted else value) + after
        node.set(SPACE, "preserve")
        inserted = True
    if start == end:
        insert_at(paragraph, nodes, start, value)


def insert_at(paragraph, nodes, position, value):
    """Вставляет текст в позицию курсора."""
    offset = 0
    for node, text in nodes:
        if node.tag == W + "t" and offset <= position <= offset + len(text):
            index = position - offset
            node.text = text[:index] + value + text[index:]
            node.set(SPACE, "preserve")
            return
        if position == offset:
            added = etree.Element(W + "t")
            added.text = value
            added.set(SPACE, "preserve")
            node.addprevious(added)
            return
        offset += len(text)
    run = etree.SubElement(paragraph, W + "r")
    added = etree.SubElement(run, W + "t")
    added.text = value
    added.set(SPACE, "preserve")


class WordForm:
    def __init__(self, content: bytes):
        """Открывает редактируемые части исходного DOCX."""
        self.content = content
        try:
            with ZipFile(BytesIO(content)) as archive:
                if sum(entry.file_size for entry in archive.infolist()) > 48 * 1024 * 1024:
                    raise ValueError("Слишком большой бланк.")
                self.parts = {name: etree.fromstring(archive.read(name), etree.XMLParser(resolve_entities=False))
                              for name in sorted(archive.namelist()) if PART.fullmatch(name)}
                if "word/document.xml" not in self.parts:
                    raise ValueError("В файле нет документа Word.")
        except (BadZipFile, etree.XMLSyntaxError) as error:
            raise ValueError("Не удалось открыть бланк DOCX.") from error
        self.paragraphs = [p for root in self.parts.values() for p in root.iter(W + "p")]

    def blocks(self):
        """Готовит абзацы для выделения текста в редакторе."""
        result = []
        for paragraph in self.paragraphs:
            alignment = paragraph.find(f"{W}pPr/{W}jc")
            result.append({"text": "".join(text for _, text in tokens(paragraph)),
                           "align": alignment.get(W + "val") if alignment is not None else None})
        return result

    def edit(self, edits, components):
        """Применяет правки сотрудника последовательно."""
        for edit in edits:
            if edit.paragraph >= len(self.paragraphs):
                raise ValueError("Абзац изменился. Откройте шаблон заново.")
            value = edit.text
            if edit.component is not None:
                if edit.component not in components:
                    raise ValueError("Неизвестный компонент.")
                value = "{{ " + edit.component + " }}"
            replace_range(self.paragraphs[edit.paragraph], edit.start, edit.end, value)

    def keys(self):
        """Возвращает уникальные поля в порядке заполнения."""
        return list(dict.fromkeys(key for block in self.blocks() for key in MARKER.findall(block["text"])))

    def fill(self, values):
        """Подставляет данные в маркеры как обычный текст Word."""
        for paragraph in self.paragraphs:
            text = "".join(value for _, value in tokens(paragraph))
            for match in reversed(list(MARKER.finditer(text))):
                replace_range(paragraph, match.start(), match.end(), values[match[1]])

    def serialize(self):
        """Сохраняет изменённые части в копию исходного файла."""
        result = BytesIO()
        with ZipFile(BytesIO(self.content)) as original, ZipFile(result, "w") as output:
            for entry in original.infolist():
                root = self.parts.get(entry.filename)
                data = original.read(entry) if root is None else etree.tostring(root, encoding="UTF-8", xml_declaration=True)
                output.writestr(entry, data)
        return result.getvalue()
