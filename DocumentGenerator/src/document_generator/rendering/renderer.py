import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from docxtpl import DocxTemplate
from jinja2 import Environment, StrictUndefined

from ..errors import DocumentError
from ..templates.schemas import DocumentTemplate, FieldValue
from .validator import FieldValidator

logger = logging.getLogger(__name__)


class DocumentRenderer:
    def __init__(self, output_dir: Path):
        """Задаёт папку готовых документов."""
        self.output_dir = output_dir

    def render(self, template: DocumentTemplate, values: dict[str, FieldValue]) -> Path:
        """Заполняет бланк и возвращает путь к файлу."""
        context = FieldValidator.context(template, values)
        target = self.output_dir / f"{template.id}_{uuid4().hex}.docx"
        try:
            document = DocxTemplate(template.path)
            document.render(context, jinja_env=Environment(undefined=StrictUndefined, autoescape=True))
            self._save(document, target)
        except Exception as error:
            logger.error("Ошибка рендеринга %s: %s", template.id, type(error).__name__)
            raise DocumentError("Не удалось создать DOCX. Проверь бланк и папку вывода.") from None
        return target.resolve()

    @staticmethod
    def _save(document: DocxTemplate, target: Path) -> None:
        """Публикует DOCX после полной записи."""
        target.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
        try:
            document.save(temporary)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
