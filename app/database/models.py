from datetime import datetime
from sqlalchemy import func, ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from typing import Optional

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
    vectorized: Mapped[bool] = mapped_column(server_default=text('false'), default=False)
    #authority_score: Mapped[float] = mapped_column(float, default=1.0)
    #momentum_score: Mapped[float] = mapped_column(float, default=0.0)
