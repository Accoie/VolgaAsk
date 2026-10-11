import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import Base, Chunk


class Indexer:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def ensure_schema(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(self.engine)

    def load_file(self, chunk_file: Path) -> int:
        """Загрузить чанки из JSON-файла в БД."""
        chunks: list[dict] = json.loads(chunk_file.read_text(encoding="utf-8"))
        with Session(self.engine) as session:
            session.add_all([Chunk(**chunk) for chunk in chunks])
            session.commit()
        return len(chunks)