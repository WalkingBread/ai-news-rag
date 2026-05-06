from datetime import datetime
from sqlalchemy import func, ForeignKey, text, Text, String, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from typing import Optional, List

from app.database.types import SignedInt64


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
    content_hash: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    simhash: Mapped[int] = mapped_column(SignedInt64, index=True)


class RefinedSource(Base):
    __tablename__ = "refined_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    processed_source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    source: Mapped[str] = mapped_column()
    url: Mapped[str] = mapped_column(unique=True)
    title: Mapped[Optional[str]] = mapped_column(nullable=True)
    body: Mapped[Optional[str]] = mapped_column(nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    topics: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    authority_score: Mapped[Float] = mapped_column(Float, default=1.0)
    momentum_score: Mapped[Float] = mapped_column(Float, default=0.0)
    vectorized: Mapped[bool] = mapped_column(server_default=text('false'), default=False)