from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column()
    document_date: Mapped[str | None] = mapped_column()
    article: Mapped[str | None] = mapped_column()
    amendant: Mapped[bool] = mapped_column()
    heading: Mapped[str | None] = mapped_column()
    chunk_index: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(312))