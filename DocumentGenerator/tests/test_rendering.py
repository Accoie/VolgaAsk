import re
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

from document_generator.config import Settings
from document_generator.rendering.renderer import DocumentRenderer
from document_generator.templates.registry import TemplateRegistry

NAMESPACES = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
TEMPLATE_IDS = (
    "material_assistance",
    "money_refund",
    "change_fio",
    "change_citizenship",
    "social_scholarship",
)
VALUES = {
    "group": "ИВТ-241",
    "faculty": "Институт цифровых технологий",
    "full_name": "Орлова Анна Сергеевна",
    "inn": "012345678901",
    "phone": "+70000000000",
    "reason": "получением социальной помощи",
    "supporting_document": "Справка № 5 <копия> & выписка",
    "date": "2026-03-23",
    "study_form": "очной",
    "course": 3,
    "specialty": "Прикладная информатика",
    "tuition_basis": "с оплатой",
    "refund_purpose": "проживание в общежитии",
    "receipt_pages": 7,
    "new_name_instrumental": "Соколовой Анной Сергеевной",
    "previous_citizenship": "гражданства Республики Казахстан",
    "new_citizenship": "Российской Федерации",
    "passport_country": "России",
    "category": "получатель государственной социальной помощи",
    "supporting_documents": "Справка о назначении социальной помощи и выписка",
}


@pytest.fixture(scope="module")
def registry() -> TemplateRegistry:
    """Загружает штатные шаблоны приложения."""
    return TemplateRegistry(Settings().templates_dir)


def read_paragraphs(path: Path) -> dict[str, list[str]]:
    """Читает текст основного документа и колонтитулов."""
    parts = {}
    with ZipFile(path) as document:
        for name in document.namelist():
            if not re.fullmatch(r"word/(?:document|header\d+|footer\d+)\.xml", name):
                continue
            root = ElementTree.fromstring(document.read(name))
            parts[name] = [
                "".join(node.text or "" for node in paragraph.findall(".//w:t", NAMESPACES))
                for paragraph in root.findall(".//w:p", NAMESPACES)
            ]
    return parts


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_renders_template(template_id: str, registry: TemplateRegistry) -> None:
    """Проверяет значения на местах маркеров и постоянный текст."""
    template = registry.get(template_id)
    values = {field.key: VALUES[field.key] for field in template.fields}
    expected_values = {**values, "date": "23.03.2026"}
    marker = re.compile(r"\{\{\s*(\w+)\s*\}\}")
    expected = {
        part: [marker.sub(lambda match: str(expected_values[match[1]]), text) for text in paragraphs]
        for part, paragraphs in read_paragraphs(template.path).items()
    }
    with TemporaryDirectory(prefix="volgaask-test-") as directory:
        published = template.model_copy(update={"content": template.path.read_bytes(), "path": None})
        output = DocumentRenderer(Path(directory)).render(published, values)
        assert read_paragraphs(output) == expected
