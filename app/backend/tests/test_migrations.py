"""T4: 迁移测试（SQLite 替身验证幂等与约束）。"""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.migrations import run_migrations

EXPECTED = {"user_word_state", "word_learning_records", "word_error_records"}


def _make_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # users 表替身（外键依赖）
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(text("INSERT INTO users (id) VALUES (1)"))
    return eng


class TestMigrations:
    def test_creates_three_tables(self):
        eng = _make_engine()
        created = run_migrations(eng)
        assert EXPECTED.issubset(set(created))

    def test_idempotent(self):
        eng = _make_engine()
        run_migrations(eng)
        created = run_migrations(eng)
        assert created == []  # 第二次无新增

    def test_unique_user_word(self):
        eng = _make_engine()
        run_migrations(eng)
        from app.models import UserWordState
        from sqlalchemy.orm import sessionmaker
        sess = sessionmaker(bind=eng)()
        sess.add(UserWordState(user_id=1, word_id="V00001"))
        sess.commit()
        sess.add(UserWordState(user_id=1, word_id="V00001"))
        try:
            sess.commit()
            assert False, "应触发唯一约束"
        except IntegrityError:
            sess.rollback()
