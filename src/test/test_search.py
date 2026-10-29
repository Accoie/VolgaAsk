"""Интеграционные тесты retriever'а по корпусу документов Волгатеха.

Путь к корню проекта добавляется в sys.path в conftest.py — pytest загружает
его до импорта этого модуля, поэтому импорты AiService ниже обычные,
без noqa.

Запуск (из корня проекта):

    python -m pytest test -v

Требуется поднятый PostgreSQL (docker start ai-service-pgvector)
с проиндексированным корпусом.
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from AiService.configs.config import DatabaseConfig, ModelsConfig
from AiService.processing.retriever import Retriever

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.json"
TOP_K = 5


def _load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def retriever() -> Retriever:
    engine = create_engine(DatabaseConfig.DATABASE_URL)
    try:
        yield Retriever(engine, ModelsConfig.EMBEDDER, ModelsConfig.RERANKER)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "case",
    _load_questions(),
    ids=lambda c: c["question"],
)
def test_search_finds_expected_text(retriever: Retriever, case: dict) -> None:
    chunks = retriever.search(case["question"], top_k=TOP_K)
    texts = [c.text for c in chunks]

    missing = [
        expected
        for expected in case["expected_texts"]
        if not any(expected in t for t in texts)
    ]

    assert not missing, (
        f"Вопрос: {case['question']}\n"
        f"Не найдены подстроки: {missing}\n"
        f"Найдены: {[t[:100] for t in texts]}"
    )
