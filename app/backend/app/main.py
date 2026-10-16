"""背单词应用 FastAPI 入口。

路由前缀 /words/api/*（错题本已占用裸 /api/）。
"""
from fastapi import Depends, FastAPI

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db

settings = get_settings()

app = FastAPI(title="english-word-app", docs_url="/words/api/docs")


@app.get("/health")
def health():
    return {"status": "ok", "app": "english-word-app", "env": settings.APP_ENV}


@app.get("/words/api/auth/me")
def auth_me(user=Depends(get_current_user)):
    return user
