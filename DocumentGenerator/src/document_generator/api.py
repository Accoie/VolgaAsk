import base64
import os
import re
import shutil
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from docx import Document
from docx.table import Table
from fastapi import FastAPI
from pydantic import BaseModel

from .config import Settings
from .dialog.session import DialogSession, DialogState
from .llm.ollama import OllamaProvider
from .service import DocumentGenerator

def shared_settings() -> Settings:
    """Размещает штатные шаблоны в общем каталоге при первом запуске."""
    settings = Settings.from_env()
    root = os.getenv("DOCUMENT_TEMPLATES_DIR")
    if not root:
        return settings
    directory = Path(root)
    if not directory.exists():
        with TemporaryDirectory(dir=directory.parent) as temporary:
            source = Path(temporary) / "templates"
            shutil.copytree(settings.templates_dir, source, ignore=shutil.ignore_patterns("__pycache__", "*.py"))
            source.rename(directory)
    return replace(settings, templates_dir=directory)


settings = shared_settings()
provider = OllamaProvider(settings.ollama_host, settings.ollama_model)
generator = DocumentGenerator(settings, provider)
app = FastAPI()


class Message(BaseModel):
    question: str
    session: DialogSession | None = None
    mode: str = "auto"
    previous: DialogSession | None = None


def intent(question: str, can_revise: bool) -> str:
    """Выбирает оформление, доработку или справочный ответ."""
    opening = question.strip().casefold()
    request = re.match(r"^(?:пожалуйста[, ]+)?(?:хочу|мне нужно|мне надо|помоги|создай|оформи|составь|подготовь|заполни)\b", opening)
    has_action = re.search(r"\b(?:оформ|созда|соста[вь]|подготов|заполн)\w*", opening)
    if request and has_action and re.search(r"\b(?:заявлени|материалк|матпомощ|документ|бланк)\w*", opening):
        return "document"
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
