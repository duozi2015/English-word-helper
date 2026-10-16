"""T1: database.py 测试 — 双库引擎（MySQL 用户状态 + SQLite 词库只读）。"""
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.database as database


class TestVocabEngine:
    def test_vocab_db_readonly_connect(self):
        """词库 SQLite 引擎可查真实库（缺失则跳过）。"""
        db = Path(__file__).resolve().parent.parent.parent.parent / "output" / "vocabulary.db"
        if not db.exists():
            pytest.skip("词库未生成")
        eng = database.get_vocab_engine()
        with eng.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM vocabulary")).scalar()
        assert n == 2940

    def test_get_vocab_session(self):
        db = Path(__file__).resolve().parent.parent.parent.parent / "output" / "vocabulary.db"
        if not db.exists():
            pytest.skip("词库未生成")
        sess = database.VocabSessionLocal()
        row = sess.execute(text("SELECT word FROM vocabulary WHERE id='V00520'")).scalar()
        sess.close()
        assert row == "chance"


class TestUserEngineUrl:
    def test_mysql_url_composed(self, monkeypatch):
        """未显式给 DATABASE_URL 时按 DB_* 组装 pymysql URL。"""
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("DB_NAME", "mistake_test")
        database.get_settings.cache_clear()
        s = database.get_settings()
        url = database.user_database_url(s)
        assert url == "mysql+pymysql://u:p@127.0.0.1:3306/mistake_test?charset=utf8mb4"
        database.get_settings.cache_clear()

    def test_explicit_url_priority(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        database.get_settings.cache_clear()
        s = database.get_settings()
        assert database.user_database_url(s) == "sqlite:///:memory:"
        database.get_settings.cache_clear()

    def test_sqlite_fallback_for_tests(self, tmp_path):
        """测试环境可用 SQLite 替身当用户库。"""
        eng = create_engine(f"sqlite:///{tmp_path}/t.db")
        (sessionmaker(bind=eng))().execute(text("SELECT 1"))
