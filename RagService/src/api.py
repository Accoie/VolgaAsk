import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

import ollama
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints

from configs.config import ModelsConfig
from database.session import create_db_engine
from processing.generator import Generator
from processing.retriever import Retriever

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Подключает индекс и модели поиска."""
    engine = create_db_engine()
    try:
        app.state.search = Retriever(engine, ModelsConfig.EMBEDDER, ModelsConfig.RERANKER)
        app.state.generation = Generator(ollama.AsyncClient(), os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
        app.state.model_lock = asyncio.Lock()
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)


class Question(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    history: str = Field(default="", max_length=16000)


def event(kind: str, text: str = "") -> str:
    """Кодирует одно SSE-событие."""
    payload = json.dumps({"type": kind, "text": text}, ensure_ascii=False)
    return f"data: {payload}\n\n"


async def answer(request: Question):
    """Ищет контекст и передаёт ответ по частям."""
    try:
        async with app.state.model_lock:
            chunks = await asyncio.to_thread(app.state.search.search, request.question)
        if chunks:
            prompt = request.question
            if request.history:
                prompt = f"Предыдущие реплики:\n{request.history}\n\nТекущий вопрос: {prompt}"
            async for token in app.state.generation.generate_stream(prompt, [c.text for c in chunks]):
                yield event("token", token)
        else:
            yield event("token", "В базе пока нет документов для ответа.")
        yield event("done")
    except Exception:
        logger.exception("Ошибка генерации ответа")
        yield event("error", "Не удалось получить ответ RAG. Проверьте доступность модели.")


@app.post("/chat")
async def chat(request: Question):
    """Открывает поток ответа."""
    return StreamingResponse(answer(request), media_type="text/event-stream")
