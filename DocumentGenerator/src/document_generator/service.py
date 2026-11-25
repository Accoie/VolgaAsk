from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from .config import Settings
from .dialog.extractor import FieldExtractor
from .dialog.manager import DialogManager
from .dialog.session import DialogSession, DialogState
from .errors import DocumentError
from .llm.base import BaseLLMProvider
from .llm.ollama import OllamaProvider
from .rendering.renderer import DocumentRenderer
from .templates.registry import TemplateRegistry
from .templates.resolver import TemplateResolver
from .templates.schemas import DocumentTemplate


@dataclass
class _Conversation:
    session: DialogSession = field(default_factory=DialogSession)
    lock: Lock = field(default_factory=Lock)


class DocumentGenerator:
    def __init__(self, settings: Settings | None = None, provider: BaseLLMProvider | None = None):
        """Собирает сервис генерации документов."""
        settings = settings or Settings.from_env()
        provider = provider or OllamaProvider(settings.ollama_host, settings.ollama_model)
        self.registry = TemplateRegistry(settings.templates_dir)
        self._manager = DialogManager(
            self.registry, TemplateResolver(self.registry, provider),
            FieldExtractor(provider), DocumentRenderer(settings.output_dir),
        )
        self._sessions: dict[str, _Conversation] = {}

    def start(self, request: str) -> DialogSession:
        """Открывает сессию по запросу пользователя."""
        conversation = _Conversation()
        session_id = conversation.session.id
        self._sessions[session_id] = conversation
        return self.send_message(session_id, request)

    def _conversation(self, session_id: str) -> _Conversation:
        """Находит открытую сессию."""
        if session_id not in self._sessions:
            raise DocumentError("Сессия не найдена.")
        return self._sessions[session_id]

    def get_state(self, session_id: str) -> DialogSession:
        """Возвращает снимок состояния диалога."""
        conversation = self._conversation(session_id)
        with conversation.lock:
            return deepcopy(conversation.session)

    def get_suggested_template(self, session_id: str) -> DocumentTemplate | None:
        """Возвращает предложенный бланк."""
        session = self.get_state(session_id)
        if session.template_id:
            return self.registry.get(session.template_id).model_copy(deep=True)
        return None

    def confirm_template(self, session_id: str, accepted: bool) -> DialogSession:
        """Принимает или отклоняет бланк."""
        conversation = self._conversation(session_id)
        with conversation.lock:
            self._manager.confirm_template(conversation.session, accepted)
            return deepcopy(conversation.session)

    def send_message(self, session_id: str, message: str) -> DialogSession:
        """Передаёт реплику и возвращает ответ диалога."""
        conversation = self._conversation(session_id)
        with conversation.lock:
            session = conversation.session
            self.advance(session, message)
            return deepcopy(session)

    def advance(self, session: DialogSession, message: str, *, revise: bool = False) -> None:
        """Продолжает сохранённый диалог."""
        try:
            if revise:
                self._manager.revise(session, message)
            else:
                self._manager.handle(session, message)
        except DocumentError as error:
            session.message = str(error)

    def is_ready(self, session_id: str) -> bool:
        """Проверяет готовность к подтверждению генерации."""
        return self.get_state(session_id).state == DialogState.REVIEW

    def generate(self, session_id: str) -> Path:
        """Подтверждает сводку и возвращает готовый DOCX."""
        conversation = self._conversation(session_id)
        with conversation.lock:
            return self._manager.generate(conversation.session)

    def cancel(self, session_id: str) -> DialogSession:
        """Отменяет генерацию в выбранной сессии."""
        conversation = self._conversation(session_id)
        with conversation.lock:
            self._manager.cancel(conversation.session)
            return deepcopy(conversation.session)
