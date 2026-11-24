from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def request_json(self, instruction: str, message: str, schema: dict) -> dict:
        """Получает структурированный ответ модели."""
