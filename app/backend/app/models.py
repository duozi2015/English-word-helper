"""用户状态 ORM 模型（错题本 MySQL 中的新表；只加新表，不动其现有表）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, Integer, String, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.utcnow()


class UserWordState(Base):
    __tablename__ = "user_word_state"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_user_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 逻辑引用错题本 users.id（不建 FK——该表归错题本迁移管理）
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    word_id: Mapped[str] = mapped_column(String(6))  # 词库 V00001
    ef: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    rep_count: Mapped[int] = mapped_column(Integer, default=0)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_mode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now())


class WordLearningRecord(Base):
    __tablename__ = "word_learning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 逻辑引用错题本 users.id（不建 FK——该表归错题本迁移管理）
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    word_id: Mapped[str] = mapped_column(String(6), index=True)
    mode: Mapped[str] = mapped_column(String(10))  # card/choice/spell
    quality: Mapped[int] = mapped_column(Integer)  # 1/2/3/5
    correct: Mapped[bool] = mapped_column(Boolean, default=True)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WordErrorRecord(Base):
    __tablename__ = "word_error_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 逻辑引用错题本 users.id（不建 FK——该表归错题本迁移管理）
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    word_id: Mapped[str] = mapped_column(String(6), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    wrong_answer: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
