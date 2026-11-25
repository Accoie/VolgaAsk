import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
import pytest
from docx import Document

from document_review import DocumentReviewService
from document_review.llm.gigachat_provider import GigaChatProvider, REVIEW_PROMPT
from document_review.schemas import ReviewError


@pytest.fixture
def source():
    """Создаёт исходный DOCX с вымышленным именем."""
    doc = Document()
    doc.add_paragraph("Заявитель: Петров Пётр")
    with TemporaryDirectory() as directory:
        path = Path(directory) / "source.docx"
        doc.save(str(path))
        yield path


def local_model(instruction, data, schema):
    """Имитирует два независимых локальных вызова."""
    if "items" in schema["properties"]:
        return {"items": [{"original": "Петров Пётр", "replacement": "Соколов Антон"}]}
    assert data[0]["original"] == "Заявитель: Петров Пётр"
    assert_fake_applicant(data[0]["anonymized"])
    return {"reason": "Имя заменено", "has_leak": False}


def assert_fake_applicant(text):
    """Проверяет сохранение поля и замену имени."""
    label, name = text.split(": ")
    assert label == "Заявитель"
    assert len(name.split()) == 2
    assert not {"Петров", "Пётр"}.intersection(name.split())


@pytest.mark.parametrize("fallback", [False, True])
def test_external_review(source, monkeypatch, fallback):
    """Проверяет отправку обезличенного файла и получение отчёта."""
    file_id = str(uuid4())
    paths = []
    report = "Приложите квитанцию для подтверждения суммы."

    def respond(request):
        paths.append(request.url.path)
        if request.url.path.endswith("/oauth"):
            assert request.headers["Authorization"] == "Basic test-key"
            return httpx.Response(200, json={"access_token": "test-token"})
        assert request.headers["Authorization"] == "Bearer test-token"
        if request.url.path.endswith("/files"):
            start = request.content.index(bytes.fromhex("504b0304"))
            doc = Document(BytesIO(request.content[start:]))
            assert_fake_applicant(doc.paragraphs[0].text)
            return httpx.Response(200, json={"id": file_id})
        if request.url.path.endswith("/completions"):
            payload = json.loads(request.content)
            assert "response_format" not in payload
            messages = payload["messages"]
            assert REVIEW_PROMPT == messages[0]["content"]
            if "attachments" in messages[1]:
                assert messages[1]["attachments"] == [file_id]
                if fallback:
                    return httpx.Response(200, json={"choices": [{"finish_reason": "function_call"}]})
            else:
                assert fallback and payload["function_call"] == "none"
                assert_fake_applicant(messages[1]["content"].splitlines()[-1])
            choice = {"finish_reason": "stop", "message": {"content": report}}
            return httpx.Response(200, json={"choices": [choice]})
        return httpx.Response(200, json={})

    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "test-key")
    service = DocumentReviewService(GigaChatProvider(httpx.MockTransport(respond)))
    monkeypatch.setattr(service.model, "request_json", local_model)
    assert service.review(source, allow_external=True) == report
    chats = ["/v1/chat/completions"] * (2 if fallback else 1)
    assert paths == ["/api/v2/oauth", "/v1/files", *chats, f"/v1/files/{file_id}/delete"]


def test_external_guard(source, monkeypatch):
    """Блокирует отправку без разрешения или положительной проверки."""
    service = DocumentReviewService()
    monkeypatch.setattr(service.gateway, "review", lambda *_: pytest.fail("Вызван внешний шлюз"))
    monkeypatch.setattr(service.model, "request_json", local_model)
    assert service.check(source).safe
    with pytest.raises(ReviewError, match="разрешение"):
        service.review(source)
    monkeypatch.setattr(service.model, "request_json", lambda *args: {"reason": "Есть утечка", "has_leak": True}
                        if "has_leak" in args[-1]["properties"] else local_model(*args))
    with pytest.raises(ReviewError, match="заблокирована"):
        service.review(source, allow_external=True)


@pytest.mark.parametrize("reason", ["length", "blacklist"])
def test_completion_stop_reason(reason):
    """Проверяет повтор по лимиту и остановку при ограничении."""
    limits = []

    def respond(request):
        payload = json.loads(request.content)
        limits.append(payload["max_tokens"])
        assert payload["messages"][0]["attachments"] == ["same-file"]
        status = reason if len(limits) == 1 else "stop"
        return httpx.Response(200, json={"choices": [{"finish_reason": status, "message": {"content": "{}"}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        payload = {"messages": [{"attachments": ["same-file"]}]}
        if reason == "length":
            assert GigaChatProvider._complete(client, payload) == "{}"
            assert limits == [4096, 8192]
        else:
            with pytest.raises(ReviewError, match="blacklist"):
                GigaChatProvider._complete(client, payload)
            assert limits == [4096]


@pytest.mark.parametrize("failure", ["timeout", "unavailable", "invalid"])
def test_failed_analysis_deletes_file(monkeypatch, failure):
    """Проверяет очистку файла после ошибки внешнего анализа."""
    file_id = str(uuid4())
    paths = []

    def respond(request):
        path = request.url.path
        paths.append(path)
        if path.endswith("/oauth"):
            return httpx.Response(200, json={"access_token": "test-token"})
        if path.endswith("/files"):
            return httpx.Response(200, json={"id": file_id})
        if path.endswith("/completions"):
            if failure == "timeout":
                raise httpx.ReadTimeout("timeout", request=request)
            if failure == "unavailable":
                return httpx.Response(503)
            choice = {"finish_reason": "stop", "message": {"content": " "}}
            return httpx.Response(200, json={"choices": [choice]})
        return httpx.Response(200)

    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "test-key")
    provider = GigaChatProvider(httpx.MockTransport(respond))
    with pytest.raises(ReviewError):
        provider.review(b"synthetic")
    assert paths[-1] == f"/v1/files/{file_id}/delete"
