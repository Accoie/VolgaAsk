from typing import AsyncGenerator
from pathlib import Path
import ollama

PROMPTS_DIR = Path(__file__).parent / "prompts"

class Generator:
    def __init__(self, client: ollama.AsyncClient, model_name: str = "qwen2.5:3b"):
        self.client = client
        self.model_name = model_name

        prompt_path = PROMPTS_DIR / "prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Файл промпта не найден: {prompt_path}")
        
        self.system_prompt_template = prompt_path.read_text(encoding="utf-8")

    def _build_prompt(self, question: str, contexts: list[str]) -> str:
        """Собирает финальный промпт, подставляя контекст и вопрос в шаблон."""
        context_str = "\n\n---\n\n".join(contexts)

        return self.system_prompt_template.format(
            context_str=context_str,
            question=question
        )

    async def generate_stream(self, question: str, contexts: list[str]) -> AsyncGenerator[str, None]:
        """Генерирует ответ потоком."""
        prompt = self._build_prompt(question, contexts)
        
        stream = await self.client.generate(
            model=self.model_name,
            prompt=prompt,
            stream=True,
            options={
                "temperature": 0.1,
                "repeat_penalty": 1.3,
                "repeat_last_n": 256,
            }
        )
        
        async for chunk in stream:
            if chunk.get('response'):
                yield chunk['response']

    async def generate(self, question: str, contexts: list[str]) -> str:
        """Генерирует ответ целиком (без стриминга)."""
        prompt = self._build_prompt(question, contexts)
        response = await self.client.generate(
            model=self.model_name,
            prompt=prompt,
            stream=False,
            options={
                "temperature": 0.1,
                "repeat_penalty": 1.3,
                "repeat_last_n": 256,
            }
        )
        return response.get('response', "")