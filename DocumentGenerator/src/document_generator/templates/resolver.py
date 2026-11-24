import json
import logging
import re

from snowballstemmer import stemmer

from ..errors import ProviderError
from ..llm.base import BaseLLMProvider
from .registry import TemplateRegistry
from .schemas import DocumentTemplate

logger = logging.getLogger(__name__)


class TemplateResolver:
    def __init__(self, registry: TemplateRegistry, provider: BaseLLMProvider):
        """Подготавливает поиск по реестру."""
        self.registry = registry
        self.provider = provider

    def resolve(self, message: str) -> list[DocumentTemplate]:
        """Ищет подходящие шаблоны для запроса."""
        templates = self.registry.list_templates()
        if not templates or not message.strip():
            return []
        stem = stemmer("russian")
        query = self._phrase(stem, message)
        matches = []
        for template in templates:
            phrases = [template.title, template.description, *template.aliases]
            if any(self._phrase(stem, phrase) in query for phrase in phrases):
                matches.append(template)
        return matches or self._ask_model(message, templates)

    @staticmethod
    def _phrase(stem, text: str) -> str:
        """Нормализует словоформы для поиска фразы."""
        words = re.findall(r"\w+", text.casefold().replace("ё", "е"))
        return " " + " ".join(stem.stemWords(words)) + " "

    def _ask_model(self, message: str, templates: list[DocumentTemplate]) -> list[DocumentTemplate]:
        """Уточняет выбор среди известных документов."""
        catalog = [item.model_dump(include={"id", "title", "description", "aliases"}) for item in templates]
        ids = [item.id for item in templates]
        schema = {
            "type": "object",
            "properties": {"ids": {"type": "array", "items": {"enum": ids}}},
            "required": ["ids"],
            "additionalProperties": False,
        }
        instruction = (
            "Подбери документы для запроса. Верни объект с массивом ids. "
            "Если запрос неоднозначен, перечисли подходящие варианты. "
            "Если совпадений нет, верни пустой массив. Каталог: "
            + json.dumps(catalog, ensure_ascii=False)
        )
        result = self.provider.request_json(instruction, message, schema).get("ids")
        if not isinstance(result, list) or any(item not in ids for item in result):
            logger.warning("Ответ модели содержит некорректный список шаблонов")
            raise ProviderError("Модель не смогла выбрать документ. Уточни запрос.")
        return [item for item in templates if item.id in result]
