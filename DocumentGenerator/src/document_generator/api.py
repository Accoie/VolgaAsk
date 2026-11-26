import base64
import os
import re
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from docx import Document
from docx.table import Table
from fastapi import FastAPI
from pydantic import BaseModel

from .config import Settings
from .dialog.session import DialogSession, DialogState
from .llm.ollama import OllamaProvider
from .service import DocumentGenerator
from .templates.database import initialize
from .templates.management import router

settings = Settings.from_env()
provider = OllamaProvider(settings.ollama_host, settings.ollama_model)
generator = DocumentGenerator(settings, provider)

@asynccontextmanager
async def lifespan(app):
    """Переносит штатный каталог до приёма запросов."""
    legacy = Path(os.getenv("DOCUMENT_TEMPLATES_DIR", settings.templates_dir))
    initialize(legacy if legacy.is_dir() else settings.templates_dir)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


class Message(BaseModel):
    question: str
    session: DialogSession | None = None
    mode: str = "auto"
    previous: DialogSession | None = None


def intent(question: str, can_revise: bool) -> str:
    """Выбирает оформление, доработку или справочный ответ."""
    direct = direct_intent(question)
    if direct:
        return direct
    instruction = (
        "Определи цель сообщения. document — человек просит составить или заполнить заявление "
        "(в том числе «хочу материалку оформить»). question — спрашивает о правилах, баллах, "
        "требованиях или порядке действий. При сомнении выбирай question."
    )
    actions = ["document", "question"]
    if can_revise:
        actions.append("revise")
        instruction += " revise — просит исправить данные в последнем готовом заявлении."
    schema = {"type": "object", "properties": {"intent": {"type": "string", "enum": actions}},
              "required": ["intent"], "additionalProperties": False}
    return provider.request_json(instruction, question, schema)["intent"]


def direct_intent(question: str) -> str | None:
    """Распознаёт явную просьбу заполнить документ и справочные вопросы."""
    opening = re.sub(r"^пожалуйста[, ]+", "", question.strip().casefold())
    question_words = r"(?:как|где|когда|куда|зачем|сколько|кто|что|какие|нужно ли|надо ли)"
    if re.match(rf"^(?:а\s+)?{question_words}\b", opening):
        return "question"
    if re.search(rf"\b(?:узнать|подскажи\w*|расскажи\w*)[ ,]+{question_words}\b", opening):
        return "question"
    subject = r"\b(?:заявлени\w*|материалк\w*|матпомощ\w*|материальн\w* помощ\w*|документ\w*|бланк\w*)\b"
    if re.fullmatch(r"(?:материалк\w*|матпомощ\w*)[.!]?", opening):
        return "document"
    action = r"(?:оформ|созда|соста[вь]|подготов|заполн)\w*"
    request = rf"\b(?:хочу|нужно|надо|помоги(?:те)?)\s+(?:\w+\s+){{0,4}}?{action}\b"
    command = r"^(?:оформи|создай|составь|подготовь|заполни)(?:те)?\b"
    if re.search(subject, opening) and not re.search(r"\bне\b", opening):
        if re.search(request, opening) or re.match(command, opening):
            return "document"
    return None


def preview(path) -> str:
    """Извлекает текст абзацев и таблиц готового DOCX."""
    lines = []
    for block in Document(path).iter_inner_content():
        if isinstance(block, Table):
            lines.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
        else:
            lines.append(block.text)
    return "\n".join(lines)


@app.post("/message")
def message(request: Message):
    """Обрабатывает один шаг диалога из сохранённого состояния."""
    mode = request.mode
    if mode == "auto" and not request.session:
        mode = intent(request.question, request.previous is not None)
    if mode == "question":
        return None
    session = request.session or (request.previous if mode == "revise" else None) or DialogSession()
    session.output_path = None
    generator.advance(session, request.question, revise=mode == "revise")
    file = None
    if session.state == DialogState.GENERATED and session.output_path:
        path = session.output_path
        try:
            file = {"title": generator.registry.get(session.template_id).title,
                    "content": base64.b64encode(path.read_bytes()).decode(), "preview": preview(path)}
        finally:
            path.unlink(missing_ok=True)
        session.output_path = None
        session.message = "Документ сформирован."
    return {"answer": session.message, "session": asdict(session), "state": session.state, "file": file}
