from typing import Protocol


class LLMGateway(Protocol):
    def review(self, document: bytes) -> str:
        """Анализирует проверенную обезличенную копию."""
        ...
