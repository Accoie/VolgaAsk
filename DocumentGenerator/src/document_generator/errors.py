class DocumentError(Exception):
    """Ошибка с сообщением для пользователя."""


class ProviderError(DocumentError):
    """Ошибка обращения к языковой модели."""


class FieldError(DocumentError):
    """Некорректное значение поля."""
