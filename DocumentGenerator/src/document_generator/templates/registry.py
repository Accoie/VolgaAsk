import logging
from pathlib import Path

from docxtpl import DocxTemplate

from ..errors import DocumentError
from ..rendering.validator import FieldValidator
from .schemas import DocumentTemplate, TemplateSchema

logger = logging.getLogger(__name__)


class TemplateRegistry:
    def __init__(self, directory: Path):
        """Загружает доступные бланки."""
        self._templates: dict[str, DocumentTemplate] = {}
        self.unavailable: list[str] = []
        for folder in sorted(directory.glob("*")):
            if folder.is_dir() and not folder.name.startswith((".", "__")):
                self._register(folder)

    def _register(self, folder: Path) -> None:
        """Добавляет проверенный бланк в реестр."""
        try:
            template = self._load(folder)
            if template.id in self._templates:
                raise DocumentError("Повторяется идентификатор шаблона.")
            self._templates[template.id] = template
        except Exception as error:
            self.unavailable.append(folder.name)
            reason = str(error) if isinstance(error, DocumentError) else type(error).__name__
            logger.warning("Шаблон %s пропущен: %s", folder.name, reason)

    @staticmethod
    def _load(folder: Path) -> DocumentTemplate:
        """Сверяет схему с переменными бланка."""
        schema = TemplateSchema.model_validate_json((folder / "schema.json").read_bytes())
        path = folder / schema.template_file
        if not path.is_file():
            raise DocumentError("Отсутствует template.docx.")
        variables = DocxTemplate(path).get_undeclared_template_variables()
        keys = {field.key for field in schema.fields}
        if keys != variables:
            difference = ", ".join(sorted(keys ^ variables))
            raise DocumentError(f"Несовпадение полей DOCX и схемы: {difference}")
        template = DocumentTemplate(**schema.model_dump(), path=path)
        FieldValidator.defaults(template)
        return template

    def list_templates(self) -> list[DocumentTemplate]:
        """Возвращает доступные шаблоны."""
        return list(self._templates.values())

    def get(self, template_id: str | None) -> DocumentTemplate:
        """Находит шаблон по идентификатору."""
        if template_id is None or template_id not in self._templates:
            raise DocumentError("Шаблон недоступен.")
        return self._templates[template_id]
