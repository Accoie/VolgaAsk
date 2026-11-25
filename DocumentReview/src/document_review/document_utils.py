from io import BytesIO
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from urllib.parse import urlsplit
from urllib.request import url2pathname, urlopen
from zipfile import BadZipFile, ZipFile

MAX_BYTES = 16 * 1024 * 1024


def load_document(source: str | Path) -> BytesIO:
    """Читает DOCX по ссылке или локальному пути."""
    url = urlsplit(str(source))
    if url.scheme in {"http", "https"}:
        with urlopen(str(source), timeout=30) as response:
            data = response.read(MAX_BYTES + 1)
    else:
        if url.scheme == "file" and url.netloc not in {"", "localhost"}:
            raise ValueError("Ожидается локальная ссылка file.")
        path = Path(url2pathname(url.path)) if url.scheme == "file" else Path(source)
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Размер документа превышает 16 МиБ.")
    stream = BytesIO(data)
    try:
        with ZipFile(stream) as archive:
            if sum(item.file_size for item in archive.infolist()) > 4 * MAX_BYTES:
                raise ValueError("Слишком большой распакованный документ.")
    except BadZipFile:
        raise ValueError("Файл не является DOCX.") from None
    stream.seek(0)
    return stream


STRUCTURE = {"p", "r", "t", "tab", "br", "tbl", "tr", "tc", "tblGrid", "gridCol",
             "pPr", "rPr", "b", "i", "sectPr", "titlePg", "tcPr", "gridSpan", "vMerge"}
WRAPPERS = {"hyperlink", "ins", "sdt", "sdtContent", "smartTag", "fldSimple"}


def copy_content(source, target, references: dict) -> None:
    """Копирует текст и структуру в чистую часть DOCX."""
    for child in source:
        name = child.tag.split("}")[-1]
        if child.tag != qn("w:" + name):
            continue
        if name in WRAPPERS:
            copy_content(child, target, references)
        elif name in {"headerReference", "footerReference"}:
            copy_reference(child, target, references)
        elif name in STRUCTURE:
            node = OxmlElement("w:" + name)
            target.append(node)
            if name == "t":
                node.text = child.text
                node.set(qn("xml:space"), "preserve")
            elif name in {"gridSpan", "vMerge"} and child.get(qn("w:val")):
                value = child.get(qn("w:val"))
                if value.isdecimal() or value in {"restart", "continue"}:
                    node.set(qn("w:val"), value)
            copy_content(child, node, references)


def copy_reference(child, target, references: dict) -> None:
    """Привязывает колонтитул к разделу копии."""
    relation = references.get(child.get(qn("r:id")))
    kind = child.get(qn("w:type"))
    if relation and kind in {"default", "first", "even"}:
        node = OxmlElement("w:" + child.tag.split("}")[-1])
        node.set(qn("r:id"), relation)
        node.set(qn("w:type"), kind)
        target.append(node)


def clean_copy(source):
    """Собирает копию без вложений, истории правок и исходных метаданных."""
    target = Document()
    target.settings.odd_and_even_pages_header_footer = source.settings.odd_and_even_pages_header_footer
    target.element.body.clear()
    roots = [target.element.body]
    references = {}
    for rid, rel in source.part.rels.items():
        kind = rel.reltype.rsplit("/", 1)[-1]
        if kind not in {"header", "footer"} or rel.is_external:
            continue
        create = target.part.add_header_part if kind == "header" else target.part.add_footer_part
        part, references[rid] = create()
        part.element.clear()
        copy_content(rel.target_part.element, part.element, {})
        roots.append(part.element)
    copy_content(source.element.body, target.element.body, references)
    return target, roots


def text_nodes(paragraph) -> list:
    """Возвращает текстовые узлы абзаца."""
    return paragraph.xpath(".//w:t")


def paragraphs(data: bytes) -> list[str]:
    """Читает проверяемый текст, включая таблицы и колонтитулы."""
    _, roots = clean_copy(Document(BytesIO(data)))
    return [
        "".join(node.text or "" for node in text_nodes(p))
        for root in roots for p in root.xpath(".//w:p")
    ]
