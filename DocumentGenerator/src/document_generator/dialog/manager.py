from pathlib import Path

from ..errors import DocumentError, FieldError
from ..rendering.renderer import DocumentRenderer
from ..rendering.validator import FieldValidator, display_value
from ..templates.registry import TemplateRegistry
from ..templates.resolver import TemplateResolver
from ..templates.schemas import DocumentTemplate, TemplateField
from .extractor import FieldExtractor
from .session import DialogSession, DialogState
from .interpreter import DialogInterpreter

class DialogManager:
    def __init__(self, registry: TemplateRegistry, resolver: TemplateResolver,
                 extractor: FieldExtractor, renderer: DocumentRenderer):
        """Подключает компоненты диалога."""
        self.registry = registry
        self.resolver = resolver
        self.extractor = extractor
        self.renderer = renderer
        self.interpreter = DialogInterpreter(extractor.provider)

    def handle(self, session: DialogSession, message: str) -> None:
        """Обрабатывает сообщение в текущем состоянии."""
        if session.state in {DialogState.CANCELLED, DialogState.GENERATED}:
            return
        if session.state == DialogState.IDLE:
            self._resolve(session, message.strip())
            return
        if session.state == DialogState.COLLECTING_DATA and self._collect_list(session, message):
            return
        response = self.interpreter.interpret(message, self._context(session))
        action = response["action"]
        if action == "cancel":
            self.cancel(session)
        elif action in {"question", "unclear"}:
            self._clarify(session, response["reply"])
        elif session.state == DialogState.TEMPLATE_SUGGESTED:
            self._answer_suggestion(session, action)
        elif session.state == DialogState.REVIEW and action == "confirm":
            self.generate(session)
        elif session.state == DialogState.REVIEW and action == "reject":
            session.message = "Укажи, какое поле нужно исправить, и его новое значение."
        elif action == "data":
            self._collect(session, message, response.get("value"), response["reply"])
        else:
            self._clarify(session, response["reply"])

    def revise(self, session: DialogSession, message: str) -> None:
        """Применяет правки к полям ранее созданного документа."""
        template = self.registry.get(session.template_id)
        session.state = DialogState.REVIEW
        extracted = self.extractor.extract(template, message, None, initial=True)
        self._save_updates(session, template, extracted, "Укажи поле и его новое значение.")
        if not extracted:
            session.message += "\n" + self._review(session, template)

    def _clarify(self, session: DialogSession, reply: str) -> None:
        """Отвечает и возвращает пользователя к текущему шагу."""
        template = self.registry.get(session.template_id)
        current = self._missing(session, template)
        prompt = current.question if session.state == DialogState.COLLECTING_DATA and current else ""
        if prompt and prompt.casefold() in reply.casefold():
            prompt = ""
        session.message = "\n".join(filter(None, (reply.strip(), prompt))) or "Уточни, пожалуйста, свой ответ."

    def _context(self, session: DialogSession) -> str:
        """Описывает модели текущий шаг диалога."""
        template = self.registry.get(session.template_id)
        current = self._missing(session, template)
        fields = ", ".join(field.caption for field in template.fields)
        context = f"Документ: {template.title}. Поля заявления: {fields}. Этап: {session.state}. "
        if session.state == DialogState.TEMPLATE_SUGGESTED:
            return context + "Ожидается согласие заполнить предложенный документ."
        if current:
            return context + f"Текущее поле: {current.caption}. Вопрос: {current.question}"
        return context + "Данные показаны для проверки. Ожидается подтверждение создания или исправления."

    def _resolve(self, session: DialogSession, message: str) -> None:
        """Предлагает бланк или просит уточнить выбор."""
        if session.candidates and message.isdecimal():
            choices = {str(i): key for i, key in enumerate(session.candidates, 1)}
            if message not in choices:
                session.message = "Выбери номер из списка.\n" + self._choices(session)
                return
            matches = [self.registry.get(choices[message])]
        else:
            matches = self.resolver.resolve(message)
            if matches:
                session.initial_messages.append(message)
            else:
                session.initial_messages.clear()
        session.candidates = [template.id for template in matches]
        if len(matches) == 1:
            session.template_id = matches[0].id
            session.state = DialogState.TEMPLATE_SUGGESTED
            session.message = f"Я нашёл документ «{matches[0].title}». Заполнить его?"
        elif matches:
            session.message = "Какой документ нужен? Укажи номер или уточни запрос.\n" + self._choices(session)
        else:
            session.message = "Подходящий шаблон не найден. Опиши, какое заявление нужно."

    def _choices(self, session: DialogSession) -> str:
        """Перечисляет предложенные документы."""
        return "\n".join(
            f"{number}. {self.registry.get(key).title}"
            for number, key in enumerate(session.candidates, 1)
        )

    def _answer_suggestion(self, session: DialogSession, answer: str) -> None:
        """Обрабатывает ответ на предложение заполнить бланк."""
        if answer in {"confirm", "reject"}:
            self.confirm_template(session, answer == "confirm")
        else:
            session.message = "Хочешь заполнить этот документ или подобрать другой?"

    def confirm_template(self, session: DialogSession, accepted: bool) -> None:
        """Начинает заполнение или возвращается к поиску."""
        if session.state != DialogState.TEMPLATE_SUGGESTED:
            raise DocumentError("Сначала выбери шаблон.")
        if not accepted:
            session.initial_messages.clear()
            session.candidates.clear()
            session.template_id = None
            session.state = DialogState.IDLE
            session.message = "Какой другой документ нужно найти?"
            return
        template = self.registry.get(session.template_id)
        values = FieldValidator.defaults(template)
        message = "\n".join(session.initial_messages)
        extracted = self.extractor.extract(template, message, None, initial=True) if message else {}
        updates, errors = self._validate_updates(template, extracted)
        values.update(updates)
        session.values = values
        session.initial_messages.clear()
        session.candidates.clear()
        self._next_question(session, template)
        self._show_missing(session, template, errors)

    def _show_missing(self, session: DialogSession, template: DocumentTemplate, errors: list[str]) -> None:
        """Показывает, что осталось заполнить."""
        missing = [field.caption for field in template.fields if field.required and field.key not in session.values]
        notices = errors[:]
        if missing:
            notices.append(
                "Осталось указать: " + ", ".join(missing) + ". Можно прислать всё через запятую в этом порядке."
            )
        session.message = "\n".join([*notices, session.message])

    @staticmethod
    def _missing(session: DialogSession, template: DocumentTemplate) -> TemplateField | None:
        """Находит первое незаполненное обязательное поле."""
        return next((f for f in template.fields if f.required and f.key not in session.values), None)

    def _collect_list(self, session: DialogSession, message: str) -> bool:
        """Принимает список ответов на недостающие поля."""
        if "," not in message:
            return False
        template = self.registry.get(session.template_id)
        missing = [field for field in template.fields if field.required and field.key not in session.values]
        if len(missing) < 2:
            return False
        extracted = self.extractor.extract(template, message, missing[0], ordered=missing)
        if not extracted:
            return False
        self._save_updates(session, template, extracted, "")
        return True

    def _collect(self, session: DialogSession, message: str, value: object, reply: str) -> None:
        """Сохраняет проверенные значения из одного сообщения."""
        template = self.registry.get(session.template_id)
        current = self._missing(session, template)
        extracted = self.extractor.extract(template, message, current)
        if current and current.key not in extracted and self.extractor.is_quoted(value, message):
            extracted[current.key] = value
        self._save_updates(session, template, extracted, reply)

    def _save_updates(self, session: DialogSession, template: DocumentTemplate, extracted: dict, reply: str) -> None:
        """Сохраняет значения и продолжает диалог."""
        updates, errors = self._validate_updates(template, extracted)
        if not updates and not errors:
            self._clarify(session, reply)
            return
        session.values.update(updates)
        self._next_question(session, template)
        if errors:
            self._show_missing(session, template, errors)

    @staticmethod
    def _validate_updates(template: DocumentTemplate, extracted: dict) -> tuple[dict, list[str]]:
        """Проверяет каждое значение отдельно."""
        updates, errors = {}, []
        for field in template.fields:
            if field.key in extracted:
                try:
                    updates[field.key] = FieldValidator.validate(field, extracted[field.key])
                except FieldError as error:
                    errors.append(f"«{field.caption}». {error}")
        return updates, errors

    def _next_question(self, session: DialogSession, template: DocumentTemplate) -> None:
        """Выбирает следующий вопрос или показывает сводку."""
        current = self._missing(session, template)
        if current:
            session.state = DialogState.COLLECTING_DATA
            session.message = current.question
        else:
            session.state = DialogState.REVIEW
            session.message = self._review(session, template)

    @staticmethod
    def _review(session: DialogSession, template: DocumentTemplate) -> str:
        """Показывает поля перед созданием документа."""
        lines = [f"Проверь данные для документа «{template.title}»."]
        for field in template.fields:
            value = session.values.get(field.key)
            shown = display_value(value) if value is not None else "не указано"
            lines.append(f"{field.caption}: {shown}")
        lines.append("Подтверди создание DOCX или укажи, что нужно исправить.")
        return "\n".join(lines)

    def generate(self, session: DialogSession) -> Path:
        """Создаёт документ после подтверждения сводки."""
        if session.state == DialogState.GENERATED and session.output_path is not None:
            return session.output_path
        if session.state != DialogState.REVIEW:
            raise DocumentError("Сначала заполни обязательные поля и проверь данные.")
        template = self.registry.get(session.template_id)
        path = self.renderer.render(template, session.values)
        session.output_path = path
        session.state = DialogState.GENERATED
        session.message = f"Документ создан: {path}"
        return path

    @staticmethod
    def cancel(session: DialogSession) -> None:
        """Завершает сессию и очищает введённые данные."""
        if session.state == DialogState.GENERATED:
            raise DocumentError("Документ уже создан.")
        session.state = DialogState.CANCELLED
        session.template_id = None
        session.candidates.clear()
        session.values.clear()
        session.initial_messages.clear()
        session.message = "Создание документа отменено."
