"""背单词应用 FastAPI 入口。

路由前缀 /words/api/*（错题本已占用裸 /api/）。
"""
from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(title="english-word-app", docs_url="/words/api/docs")


@app.get("/health")
def health():
    return {"status": "ok", "app": "english-word-app", "env": settings.APP_ENV}
