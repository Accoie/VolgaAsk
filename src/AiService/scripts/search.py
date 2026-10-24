import argparse
import json
import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..configs.config import DatabaseConfig, ModelsConfig
from ..processing.retriever import Retriever


logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search indexed document chunks.")
    parser.add_argument("query", help="Text to search for")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    return args


def _create_retriever(engine: Engine) -> Retriever:
    return Retriever(engine, ModelsConfig.EMBEDDER, ModelsConfig.RERANKER)


def _search(engine: Engine, query: str, top_k: int) -> list[dict[str, object]]:
    retriever = _create_retriever(engine)
    chunks = retriever.search(question=query, top_k=top_k)
    return [chunk.to_dict() for chunk in chunks]


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    engine = create_engine(DatabaseConfig.DATABASE_URL)

    try:
        results = _search(engine, args.query, args.top_k)
    except Exception as error:
        logger.error("Search failed: %s", error)
        return 1
    finally:
        engine.dispose()

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())