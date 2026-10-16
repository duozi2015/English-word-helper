"""幂等建表迁移：只创建词汇应用的新表，绝不改动错题本现有表。"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.models import Base


def run_migrations(engine: Engine) -> list[str]:
    """创建词汇应用新表（幂等）。返回创建的表名列表。"""
    before = set(
        row[0] for row in engine.connect().exec_driver_sql("SHOW TABLES")
    ) if engine.dialect.name == "mysql" else set(
        row[0] for row in engine.connect().exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'")
    )
    Base.metadata.create_all(engine)
    after = set(
        row[0] for row in engine.connect().exec_driver_sql("SHOW TABLES")
    ) if engine.dialect.name == "mysql" else set(
        row[0] for row in engine.connect().exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'")
    )
    return sorted(after - before)
