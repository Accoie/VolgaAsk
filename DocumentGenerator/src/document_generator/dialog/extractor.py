import json
import logging
import re

from ..errors import ProviderError
from ..llm.base import BaseLLMProvider
from ..templates.schemas import DocumentTemplate, TemplateField

logger = logging.getLogger(__name__)


class FieldExtractor:
    def __init__(self, provider: BaseLLMProvider):
        """Сохраняет провайдер модели."""
        self.provider = provider

    def extract(
        self, template: DocumentTemplate, message: str, current: TemplateField | None, *,
        initial: bool = False, ordered: list[TemplateField] | None = None,
    ) -> dict[str, str]:
        """Извлекает явно указанные значения из сообщения."""
        labels = {field.key: field.caption for field in template.fields}
        if initial:
            names = sorted([template.title, *template.aliases], key=len, reverse=True)
            prefix = "|".join(re.escape(name) for name in names)
            message = re.sub(rf"^(?:{prefix})\s*(?:[,.:;—-]\s*|$)", "", message, flags=re.IGNORECASE)
            if not message:
                return {}
        return self._extract_fields(labels, message, current, initial, ordered)

    def _extract_fields(
        self, labels: dict[str, str], message: str, current: TemplateField | None,
        check_all: bool, ordered: list[TemplateField] | None,
    ) -> dict[str, str]:
        """Запрашивает значения заданных полей."""
        schema = {
            "type": "object",
            "properties": {key: {"type": ["string", "null"]} for key in labels},
            "additionalProperties": False,
        }
        instruction = self._instruction(labels, current)
        if check_all:
            schema["required"] = list(labels)
            instruction = (
                "Извлеки данные для заявления из сообщения. Игнорируй просьбу оформить документ. "
                "Заполни все явно указанные поля. Для остальных верни null. "
                "ФИО из трёх слов запиши только в full_name. Фамилия и имя не относятся к факультету. "
                "Копируй значения дословно. Телефон и ИНН копируй строкой, включая знаки и ведущие нули. "
                "Например, «телефон +70000000000» даёт phone со значением «+70000000000». "
                "Ключи полей и их значения по смыслу: " + json.dumps(labels, ensure_ascii=False)
            )
        if ordered:
            order = ", ".join(f"{field.key} ({field.caption})" for field in ordered)
            instruction = (
                "Разбери список ответов на вопросы анкеты. Если значения перечислены без названий, "
                "сопоставь их по порядку: " + order + ". "
                "Если ответов меньше, учитывай смысл каждого значения и оставляй пропуски. "
                "Если реплика является вопросом или командой без данных, верни пустой объект. "
                "Если пользователь назвал поля явно, сопоставь по названиям. "
                "Копируй значения дословно, включая знаки, цифры и регистр. "
                "Не придумывай пропущенные значения. Поля: " + json.dumps(labels, ensure_ascii=False)
            )
        result = self.provider.request_json(instruction, message, schema)
        if result.keys() - labels.keys():
            logger.warning("В ответе модели присутствуют неизвестные поля")
            raise ProviderError("Модель вернула некорректный ответ. Повтори сообщение.")
        return {key: value for key, value in result.items() if self.is_quoted(value, message)}

    @staticmethod
    def _instruction(labels: dict[str, str], current: TemplateField | None) -> str:
        """Собирает инструкцию для извлечения полей."""
        focus = f"{current.key} — {current.question or current.caption}" if current else "текущего поля нет, ищи явно указанные данные"
        return (
            "Извлеки только данные заявителя из последнего сообщения. "
            "Каждое значение копируй дословно из сообщения, без пояснений и догадок. "
            "Короткий ответ без названия поля относится к текущему вопросу. "
            "Учитывай явные исправления и несколько полей за раз. "
            "Если сообщение начинается с просьбы оформить заявление, пропусти эту просьбу и извлеки данные после неё. "
            "Верни объект со всеми прямо указанными полями. Отсутствующие пропусти. "
            "Пример: «Я Петров Пётр Петрович, группа АБ-123» — "
            '{"full_name":"Петров Пётр Петрович","group":"АБ-123"}. '
            "Если данных нет, верни {}. "
            f"Текущий вопрос: {focus}. Поля: " + json.dumps(labels, ensure_ascii=False)
        )

    @staticmethod
    def is_quoted(value: object, message: str) -> bool:
        """Проверяет, что значение взято из ответа пользователя."""
        if not isinstance(value, str) or not value.strip():
            return False
        pattern = r"(?<!\w)" + re.escape(value.strip()) + r"(?!\w)"
        return re.search(pattern, message, re.IGNORECASE) is not None

