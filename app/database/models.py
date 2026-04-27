from datetime import datetime
from sqlalchemy import func, ForeignKey, Index, Text, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from typing import Optional

from app.settings import VECTOR_DIMENSIONS

class Base(DeclarativeBase):
    pass

class RawSource(Base):
    __tablename__ = "raw_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column()
    url: Mapped[str] = mapped_column(unique=True)
    title: Mapped[Optional[str]] = mapped_column(nullable=True)
    body: Mapped[Optional[str]] = mapped_column(nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProcessedSource(Base):
    __tablename__ = "source"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_source_id: Mapped[int] = mapped_column(ForeignKey("raw_source.id"))
    source: Mapped[str] = mapped_column()
    url: Mapped[str] = mapped_column(unique=True)
    title: Mapped[Optional[str]] = mapped_column(nullable=True)
    body: Mapped[Optional[str]] = mapped_column(nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SourceChunk(Base):
    __tablename__ = "source_chunk"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Vector] = mapped_column(Vector(VECTOR_DIMENSIONS))

    __table_args__ = (
        Index(
            "hnsw_index_chunks",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )