import re
"""背单词应用 FastAPI 入口。

路由前缀 /words/api/*（错题本已占用裸 /api/）。
"""
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app import mistake_client
from app.config import get_settings
from app.database import get_db

settings = get_settings()
REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent.parent.parent

app = FastAPI(title="english-word-app", docs_url="/words/api/docs")


@app.get("/health")
def health():
    return {"status": "ok", "app": "english-word-app", "env": settings.APP_ENV}


@app.post("/words/api/auth/login")
def login(body: dict):
    """登录：主路透传错题本（零复制用户管理）；错题本不可达时后备直验同库 bcrypt。"""
    username = body.get("username", "")
    password = body.get("password", "")
    try:
        r = httpx.post(f"{settings.MISTAKEBOOK_API}/api/v1/auth/login",
                       json={"username": username, "password": password},
                       timeout=5)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except (httpx.HTTPError, ValueError):
        pass  # 上游不可达 → 后备登录
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4
    from jose import jwt as jose_jwt
    from passlib.context import CryptContext
    from sqlalchemy import text as _text

    from app.database import UserSessionLocal

    fresh = get_settings()  # 测试环境密钥可能被 monkeypatch，取新鲜配置
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    with UserSessionLocal() as db:  # type: ignore[call-arg]
        row = db.execute(
            _text("SELECT id, username, password_hash FROM users WHERE username = :u"),
            {"u": username},
        ).mappings().first()
    if not row or not ctx.verify(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    now = datetime.now(timezone.utc)
    claims = lambda typ, mins: {  # noqa: E731
        "sub": str(row["id"]), "username": row["username"], "jti": str(uuid4()),
        "type": typ, "exp": now + timedelta(minutes=mins), "iat": now}
    return {
        "access_token": jose_jwt.encode(claims("access", 1440), fresh.JWT_SECRET,
                                        algorithm=fresh.JWT_ALGORITHM),
        "refresh_token": jose_jwt.encode(claims("refresh", 10080), fresh.JWT_SECRET,
                                         algorithm=fresh.JWT_ALGORITHM),
        "token_type": "bearer",
        "_fallback": True,  # 标记：错题本不可达时的后备登录
    }


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


_TTS_CACHE = REPO_ROOT / "app" / "backend" / "tts_cache"
_TTS_OK = re.compile(r"^[A-Za-z0-9 .,'&-]{1,60}$")  # 词形白名单，防注入


@app.get("/words/api/tts/{word}.m4a")
def tts(word: str):
    """macOS say 合成发音，磁盘缓存。"""
    import subprocess
    if not _TTS_OK.fullmatch(word):
        raise HTTPException(status_code=400, detail="非法词形")
    _TTS_CACHE.mkdir(parents=True, exist_ok=True)
    out = _TTS_CACHE / f"{word}.m4a"
    if not out.exists():
        tmp = out.with_suffix(".tmp.m4a")
        r = subprocess.run(
            ["say", "-v", "Samantha", "-o", str(tmp), word],
            capture_output=True, timeout=10)
        if r.returncode != 0:
            raise HTTPException(status_code=500, detail="TTS 失败")
        tmp.rename(out)
    return FileResponse(out, media_type="audio/mp4")


@app.get("/words/api/stats")
def get_stats(user=Depends(get_current_user), db=Depends(get_db)):
    from app import review_service
    return review_service.stats(db, user["id"])


@app.get("/words/api/quiz/choice/{word_id}")
def choice_quiz(word_id: str):
    """四选一题组：正确释义 + 同词性干扰项（已打乱）。"""
    import random
    from app import vocab_store
    rec = vocab_store.get_by_id(word_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="词条不存在")
    pos = rec["meanings"][0]["pos"] if rec["meanings"] else ""
    distractors = vocab_store.choice_distractors(word_id, pos, 3)
    options = [m["meaning"] for m in rec["meanings"][:1]] + distractors
    random.shuffle(options)
    return {"word_id": word_id, "word": rec["word"],
            "correct": rec["meanings"][0]["meaning"] if rec["meanings"] else "",
            "options": options}
