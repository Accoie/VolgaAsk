import re
from datetime import date, datetime

from ..errors import FieldError
from ..templates.schemas import DocumentTemplate, FieldValue, TemplateField


class FieldValidator:
    @classmethod
    def validate(cls, field: TemplateField, value: object) -> FieldValue:
        """Приводит значение к типу поля."""
        if type(value) not in (str, int, bool):
            raise FieldError("Укажи одно значение.")
        text = str(value).strip()
        if not text or re.search(r"[\x00-\x08\x0b-\x1f]", text):
            raise FieldError("Введи непустое значение без управляющих символов.")
        if field.type == "integer":
            return cls._integer(field, text)
        if field.type == "date":
            return cls._date(text)
        if field.type == "boolean":
            return cls._boolean(text)
        if field.type in {"choice", "enum"}:
            return cls._choice(field, text)
        if not isinstance(value, str):
            raise FieldError("Введи текст.")
        return text

    @staticmethod
    def _integer(field: TemplateField, text: str) -> int:
        """Проверяет целое число и его границы."""
        if not re.fullmatch(r"[+-]?[0-9]+", text):
            raise FieldError("Введи целое число.")
        try:
            number = int(text)
        except ValueError:
            raise FieldError("Слишком длинное число.") from None
        bounds = field.constraints
        if bounds.min is not None and number < bounds.min:
            raise FieldError(f"Минимальное значение — {bounds.min}.")
        if bounds.max is not None and number > bounds.max:
            raise FieldError(f"Максимальное значение — {bounds.max}.")
        return number

    @staticmethod
    def _date(text: str) -> str:
        """Форматирует дату для заявления."""
        if text.casefold() in {"сегодня", "today"}:
            return date.today().strftime("%d.%m.%Y")
        for pattern in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, pattern).strftime("%d.%m.%Y")
            except ValueError:
                continue
        raise FieldError("Укажи существующую дату в формате ДД.ММ.ГГГГ.")

    @staticmethod
    def _boolean(text: str) -> bool:
        """Распознаёт логическое значение."""
        if text.casefold() in {"да", "true"}:
            return True
        if text.casefold() in {"нет", "false"}:
            return False
        raise FieldError("Ответь «да» или «нет».")

    @staticmethod
    def _choice(field: TemplateField, text: str) -> str:
        """Находит значение среди допустимых вариантов."""
        for option in field.options:
            if text.casefold() == option.casefold():
                return option
        raise FieldError("Выбери один из вариантов: " + ", ".join(field.options))

    @classmethod
    def defaults(cls, template: DocumentTemplate) -> dict[str, FieldValue]:
        """Готовит начальные значения полей."""
        return {
            field.key: cls.validate(field, field.default)
            for field in template.fields if field.default is not None
        }

    @classmethod
    def context(cls, template: DocumentTemplate, values: dict) -> dict:
        """Проверяет данные перед подстановкой в DOCX."""
        if values.keys() - {field.key for field in template.fields}:
            raise FieldError("В данных есть неизвестные поля.")
        result = {}
        for field in template.fields:
            if field.key in values:
                result[field.key] = display_value(cls.validate(field, values[field.key]))
            elif field.required:
                raise FieldError(f"Заполни поле «{field.caption}».")
            else:
                result[field.key] = ""
        return result


def display_value(value: FieldValue) -> str:
    """Готовит значение для показа пользователю."""
    if isinstance(value, bool):
        return "да" if value else "нет"
    return str(value)
