from io import BytesIO
from pathlib import Path

from document_review.anonymizer import anonymize
from document_review.llm.ollama_provider import OllamaProvider
from document_review.document_utils import load_document

from .anonymization_checker import AnonymizationChecker
from .llm.gateway import LLMGateway
from .llm.gigachat_provider import GigaChatProvider
from .schemas import CheckResult, ReviewError


class DocumentReviewService:
    def __init__(self, gateway: LLMGateway | None = None):
        """Подключает локальную модель и внешний шлюз."""
        self.model = OllamaProvider()
        self.checker = AnonymizationChecker(self.model)
        self.gateway = gateway if gateway is not None else GigaChatProvider()

    def _prepare(self, source: str | Path) -> tuple[bytes, CheckResult]:
        """Обезличивает и проверяет одну копию в памяти."""
        with load_document(source) as stream:
            original = stream.getvalue()
            copy = anonymize(BytesIO(original), self.model)
        return copy, self.checker.check(original, copy)

    def check(self, source: str | Path) -> CheckResult:
        """Выполняет только локальные этапы."""
        _, result = self._prepare(source)
        return result

    def review(
        self, source: str | Path, *, allow_external: bool = False
    ) -> str:
        """Передаёт проверенную копию после явного разрешения."""
        if allow_external is not True:
            raise ReviewError("Для этого документа требуется явное разрешение внешней отправки.")
        copy, result = self._prepare(source)
        if not result.safe:
            raise ReviewError("Qwen обнаружила риск раскрытия данных. Отправка заблокирована.")
        return self.gateway.review(copy)
