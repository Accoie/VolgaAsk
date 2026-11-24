import json
import logging
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ..errors import ProviderError
from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    def __init__(self, host: str, model: str):
        """Настраивает подключение к Ollama."""
        self.endpoint = host.rstrip("/") + "/api/chat"
        self.model = model

    def request_json(self, instruction: str, message: str, schema: dict) -> dict:
        """Запрашивает JSON по заданной схеме."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": message},
            ],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        }
        response = self._post(payload)
        try:
            content = json.loads(response)["message"]["content"]
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (ValueError, KeyError, TypeError) as error:
            logger.warning("Некорректный формат ответа Ollama: %s", type(error).__name__)
            raise ProviderError("Модель вернула некорректный ответ. Повтори сообщение.") from None

    def _post(self, payload: dict) -> bytes:
        """Отправляет запрос локальной модели."""
        try:
            request = Request(
                self.endpoint,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urlopen(request, timeout=120) as response:
                return response.read()
        except HTTPError as error:
            logger.warning("Ollama вернула HTTP %d", error.code)
            raise ProviderError("Ollama отклонила запрос. Проверь установленную модель.") from None
        except (OSError, ValueError, HTTPException) as error:
            logger.warning("Ошибка подключения к Ollama: %s", type(error).__name__)
            raise ProviderError("Ollama недоступна. Проверь адрес и повтори сообщение.") from None
