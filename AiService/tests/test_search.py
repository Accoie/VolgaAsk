import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from configs.config import ModelsConfig
from database.session import create_db_engine
from processing.retriever import Retriever

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.json"
TOP_K = 5


def _load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    engine = create_db_engine()
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def retriever(engine: Engine) -> Iterator[Retriever]:
    yield Retriever(engine, ModelsConfig.EMBEDDER, ModelsConfig.RERANKER)


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
