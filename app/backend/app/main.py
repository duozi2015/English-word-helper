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


@app.get("/words/api/words/{word_id}")
def word_detail(word_id: str):
    from app import vocab_store
    rec = vocab_store.get_by_id(word_id)
    if rec is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="词条不存在")
    return rec


@app.get("/words/api/units")
def unit_list():
    from app import vocab_store
    return vocab_store.units()


@app.get("/words/api/units/{grade}/{semester}/{unit}")
def unit_word_list(grade: str, semester: str, unit: str):
    from app import vocab_store
    return vocab_store.unit_words(grade, semester, unit)
