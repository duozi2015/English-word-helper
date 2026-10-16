"""背单词应用配置（第二阶段）。

JWT_SECRET 与错题本同源（读其仓库根 .env）；MySQL 用户状态 / SQLite 词库只读。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根（app/backend/app/config.py → 上溯三级）
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# 错题本仓库（同机约定路径；可用环境变量覆盖）
MISTAKE_REPO = Path(__file__).resolve().parent.parent.parent.parent / ".." / "mistake_notebook"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / "app" / ".env", extra="ignore")

    APP_ENV: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8001

    # JWT：与错题本同 secret、同算法
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # 用户状态库（MySQL；开发连 mistake_test，生产 mistake_prod）
    DATABASE_URL: str = ""          # 显式指定优先
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "mistake_test"
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    # 词库（第一阶段产物，只读）
    VOCAB_DB: str = str(REPO_ROOT / "output" / "vocabulary.db")

    # 错题本联动
    MISTAKEBOOK_API: str = "http://127.0.0.1:8000"
    LINK_MISTAKEBOOK: bool = True


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.JWT_SECRET or s.JWT_SECRET == "dev-secret-change-in-production":
        # 尝试从错题本仓库根 .env 读取生产 secret
        env_file = MISTAKE_REPO / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("JWT_SECRET="):
                    s.JWT_SECRET = line.split("=", 1)[1].strip()
                    break
    return s
