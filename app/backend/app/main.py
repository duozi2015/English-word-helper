"""背单词应用 FastAPI 入口。

路由前缀 /words/api/*（错题本已占用裸 /api/）。
"""
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user
from app import mistake_client
from app.config import get_settings
from app.database import get_db

settings = get_settings()

app = FastAPI(title="english-word-app", docs_url="/words/api/docs")


@app.get("/health")
def health():
    return {"status": "ok", "app": "english-word-app", "env": settings.APP_ENV}


@app.post("/words/api/auth/login")
def login(body: dict):
    """透传错题本登录（零复制用户管理；返回其 TokenResponse）。"""
    r = httpx.post(f"{settings.MISTAKEBOOK_API}/api/v1/auth/login",
                   json={"username": body.get("username"), "password": body.get("password")},
                   timeout=5)
    return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/words/api/auth/me")
def auth_me(user=Depends(get_current_user)):
    return user


class ReviewIn(BaseModel):
    word_id: str
    mode: str  # card/choice/spell
    quality: int  # 1/2/3/5
    wrong_answer: str | None = None
    response_ms: int | None = None


@app.get("/words/api/deck/today")
def deck_today(new_limit: int = 10, user=Depends(get_current_user),
               db=Depends(get_db)):
    from app import review_service
    return review_service.deck_today(db, user["id"], new_limit)


@app.post("/words/api/review")
def review(body: ReviewIn, request: Request,
           user=Depends(get_current_user), db=Depends(get_db)):
    from app import review_service
    sender = mistake_client.make_sender(request.headers.get("authorization", ""))
    try:
        return review_service.submit_review(
            db, user["id"], body.word_id, body.mode, body.quality,
            wrong_answer=body.wrong_answer, response_ms=body.response_ms,
            mistake_client=sender)
    except review_service.WordNotFound:
        raise HTTPException(status_code=404, detail="词条不存在")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


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
