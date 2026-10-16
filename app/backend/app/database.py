"""双数据库连接：MySQL（用户状态）+ SQLite 词库（只读）。"""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings


def user_database_url(s=None) -> str:
    """用户状态库连接串：显式 DATABASE_URL 优先，否则按 DB_* 组装。"""
    s = s or get_settings()
    if s.DATABASE_URL:
        return s.DATABASE_URL
    pwd = quote_plus(s.DB_PASSWORD) if s.DB_PASSWORD else ""
    auth = s.DB_USER + (f":{pwd}" if pwd else "")
    return (
        f"mysql+pymysql://{auth}@{s.DB_HOST}:{s.DB_PORT}/{s.DB_NAME}?charset=utf8mb4"
    )


@lru_cache
def get_user_engine():
    return create_engine(user_database_url(), pool_pre_ping=True, pool_recycle=3600)


@lru_cache
def get_vocab_engine():
    """词库 SQLite 只读引擎。"""
    return create_engine(f"sqlite:///{get_settings().VOCAB_DB}?mode=ro", echo=False)


UserSessionLocal = sessionmaker(bind=get_user_engine(), autoflush=False, expire_on_commit=False)
VocabSessionLocal = sessionmaker(bind=get_vocab_engine())


def get_db():
    """FastAPI 依赖：用户状态库会话。"""
    db = UserSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_vocab_db():
    """FastAPI 依赖：词库只读会话。"""
    db = VocabSessionLocal()
    try:
        yield db
    finally:
        db.close()
