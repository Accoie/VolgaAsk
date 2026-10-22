from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[str] = mapped_column(String(255), index=True)
    document_date: Mapped[str | None] = mapped_column(String(10))
    chunk_index: Mapped[int] = mapped_column(Integer)

    amendant: Mapped[bool] = mapped_column(default=False, index=True)

    headings: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    page_numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)

    text: Mapped[str] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(312))