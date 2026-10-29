"""Интеграционные тесты retriever'а по корпусу документов Волгатеха.

Запуск (из корня репозитория C:\\VolgaAsk):

    src/AiService/.venv/Scripts/python -m pytest test -v

Тесты требуют поднятого PostgreSQL (docker start ai-service-pgvector)
с проиндексированным корпусом.
"""

import json
import sys
from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import create_engine

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from AiService.configs.config import DatabaseConfig, ModelsConfig  # noqa: E402
from AiService.processing.retriever import Retriever  # noqa: E402

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.json"
TOP_K = 5


def _load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def retriever() -> Iterator[Retriever]:
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
