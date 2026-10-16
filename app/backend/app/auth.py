"""JWT 验签（与错题本账号体系打通）。

四要件缺一不可：HS256 验签 + type=="access" + jti 不在 token_blacklist + sub 在 users 表。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

security = HTTPBearer(auto_error=False)

# 错题本侧表结构的最小只读映射（不建这些表，只查询）
_SELECT_USER = text(
    "SELECT id, username, display_name, role FROM users WHERE id = :id"
)
_SELECT_BLACKLIST = text(
    "SELECT 1 FROM token_blacklist WHERE jti = :jti LIMIT 1"
)


def verify_token(token: str, db: Session | object) -> dict:
    """校验 access token，返回 payload。失败抛 401。"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证无效")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证类型错误")
    jti = payload.get("jti")
    if jti and db.execute(_SELECT_BLACKLIST, {"jti": jti}).first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证已登出")
    if not db.execute(_SELECT_USER, {"id": int(payload.get("sub", 0))}).first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = verify_token(credentials.credentials, db)
    row = db.execute(
        _SELECT_USER, {"id": int(payload["sub"])}
    ).mappings().first()
    return {"id": row["id"], "username": row["username"],
            "display_name": row["display_name"] or row["username"], "role": row["role"]}
