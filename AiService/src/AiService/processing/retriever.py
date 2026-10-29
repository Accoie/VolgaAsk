import logging

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..database.models import Chunk
from ..processing.embedder import Embedder
from ..utils.model_loader import ModelLoader


logger = logging.getLogger(__name__)


class Retriever:
    """Ищет чанки, релевантные вопросу"""

    CANDIDATES_MULTIPLIER: int = 4

    def __init__(
        self,
        engine: Engine,
        embedder_model_name: str,
        reranker_model_name: str,
    ) -> None:
        self.engine = engine
        with engine.connect():
            pass
        self.embedder = Embedder(ModelLoader.load_embedding_model(embedder_model_name))
        self.reranker = ModelLoader.load_cross_encoder(reranker_model_name)

    def search(self, question: str, top_k: int = 5) -> list[Chunk]:
        """Найти top_k чанков: быстрый поиск + rerank."""
        candidates = self._vector_search(question, top_k * self.CANDIDATES_MULTIPLIER)
        if not candidates:
            return []
        return self._rerank(candidates, question)[:top_k]

    def _vector_search(self, question: str, limit: int) -> list[Chunk]:
        query_embedding = self.embedder.embed_text(question)

        with Session(self.engine) as session:
            stmt = (
                select(Chunk)
                .order_by(Chunk.embedding.cosine_distance(query_embedding))
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def _rerank(self, candidates: list[Chunk], question: str) -> list[Chunk]:
        pairs = [(question, chunk.text) for chunk in candidates]
        scores = self.reranker.predict(pairs)

        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in ranked]