import re
from typing import AsyncGenerator
from pathlib import Path
import ollama

PROMPTS_DIR = Path(__file__).parent / "prompts"
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")
LANGUAGE_ARTIFACT = re.compile(
    r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\uf900-\ufaff\U00020000-\U000323af]"
    r"|[А-Яа-яЁё][A-Za-z]|[A-Za-z][А-Яа-яЁё]"
)
EMPTY_ANSWER = "Не удалось сформировать ответ. Попробуй уточнить вопрос."

class Generator:
    def __init__(self, client: ollama.AsyncClient, model_name: str = "qwen2.5:3b"):
        self.client = client
        self.model_name = model_name

        prompt_path = PROMPTS_DIR / "prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Файл промпта не найден: {prompt_path}")
        
        self.system_prompt_template = prompt_path.read_text(encoding="utf-8")

    def _messages(self, question: str, contexts: list[str]) -> list[dict[str, str]]:
        """Передаёт правила модели отдельно от контекста и вопроса."""
        context = "\n\n---\n\n".join(contexts)
        return [
            {"role": "system", "content": self.system_prompt_template},
            {"role": "user", "content": f"КОНТЕКСТ:\n{context}\n\nЗАПРОС:\n{question}"},
        ]

    async def generate_stream(self, question: str, contexts: list[str]) -> AsyncGenerator[str, None]:
        """Генерирует ответ потоком."""
        stream = await self.client.chat(
            model=self.model_name,
            messages=self._messages(question, contexts),
            stream=True,
            options={"temperature": 0.1, "repeat_penalty": 1.1},
        )
        pending = ""
        sent = False
        async for chunk in stream:
            pending += chunk.message.content or ""
            start = 0
            for boundary in SENTENCE_END.finditer(pending):
                part = pending[start:boundary.end()]
                if part.strip() and not LANGUAGE_ARTIFACT.search(part):
                    yield part
                    sent = True
                start = boundary.end()
            pending = pending[start:]
        if pending.strip() and not LANGUAGE_ARTIFACT.search(pending):
            yield pending
        elif not sent:
            yield EMPTY_ANSWER

    async def generate(self, question: str, contexts: list[str]) -> str:
        """Собирает ответ целиком."""
        return "".join([part async for part in self.generate_stream(question, contexts)])
