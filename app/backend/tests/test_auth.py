"""T2: auth.py 测试 — JWT 四要件验签。

用 SQLite 内存库替身 users/token_blacklist 表（结构与错题本一致），
token 用测试密钥自签，覆盖：有效/类型错/黑名单/用户不存在/过期/无头。
"""
import sys

import httpx
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt as jose_jwt
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app import auth as auth_mod
from app.auth import get_current_user, verify_token


@pytest.fixture
def user_db():
    """SQLite 内存库 + users/token_blacklist 表（列与错题本一致）。"""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50), "
            "password_hash VARCHAR(255), display_name VARCHAR(100), "
            "role VARCHAR(20) DEFAULT 'student')"))
        conn.execute(text(
            "CREATE TABLE token_blacklist (id INTEGER PRIMARY KEY, "
            "jti VARCHAR(36) UNIQUE, expires_at DATETIME)"))
        conn.execute(text(
            "INSERT INTO users (id, username, display_name, role) "
            "VALUES (1, 'dou', '小豆', 'student')"))
    return sessionmaker(bind=eng)()


def _make_token(secret, uid=1, username="dou", jti=None, typ="access",
                minutes=30, iat_offset=0):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uid), "username": username,
        "jti": jti or str(uuid4()), "type": typ,
        "exp": now + timedelta(minutes=minutes),
        "iat": now + timedelta(minutes=iat_offset),
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256"), payload["jti"]


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-xyz")
    auth_mod.get_settings.cache_clear()
    yield "test-secret-xyz"
    auth_mod.get_settings.cache_clear()


def _creds(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestVerifyToken:
    def test_valid_access(self, auth_env, user_db):
        token, jti = _make_token(auth_env)
        payload = verify_token(token, user_db)
        assert payload["sub"] == "1"
        assert payload["type"] == "access"

    def test_refresh_type_rejected(self, auth_env, user_db):
        token, _ = _make_token(auth_env, typ="refresh")
        with pytest.raises(HTTPException) as e:
            verify_token(token, user_db)
        assert e.value.status_code == 401

    def test_blacklisted_rejected(self, auth_env, user_db):
        token, jti = _make_token(auth_env)
        user_db.execute(text(
            "INSERT INTO token_blacklist (jti, expires_at) "
            "VALUES (:j, datetime('now', '+1 day'))"), {"j": jti})
        user_db.commit()
        with pytest.raises(HTTPException) as e:
            verify_token(token, user_db)
        assert e.value.status_code == 401

    def test_unknown_user_rejected(self, auth_env, user_db):
        token, _ = _make_token(auth_env, uid=999)
        with pytest.raises(HTTPException):
            verify_token(token, user_db)

    def test_expired_rejected(self, auth_env, user_db):
        token, _ = _make_token(auth_env, minutes=-10)
        with pytest.raises(HTTPException):
            verify_token(token, user_db)

    def test_wrong_secret_rejected(self, auth_env, user_db):
        token, _ = _make_token("other-secret")
        with pytest.raises(HTTPException):
            verify_token(token, user_db)


class TestGetCurrentUser:
    def test_returns_user_info(self, auth_env, user_db):
        token, _ = _make_token(auth_env)
        user = get_current_user(_creds(token), user_db)
        assert user == {"id": 1, "username": "dou", "display_name": "小豆", "role": "student"}

    def test_missing_header(self, auth_env, user_db):
        with pytest.raises(HTTPException) as e:
            get_current_user(None, user_db)
        assert e.value.status_code == 401


class TestAuthMeEndpoint:
    def test_me_with_valid_token(self, auth_env, monkeypatch):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.main import app
        from app.database import get_db

        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        with eng.begin() as conn:
            conn.execute(text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50), "
                "password_hash VARCHAR(255), display_name VARCHAR(100), "
                "role VARCHAR(20) DEFAULT 'student')"))
            conn.execute(text(
                "CREATE TABLE token_blacklist (id INTEGER PRIMARY KEY, "
                "jti VARCHAR(36) UNIQUE, expires_at DATETIME)"))
            conn.execute(text(
                "INSERT INTO users (id, username, display_name, role) "
                "VALUES (1, 'dou', '小豆', 'student')"))
        TestSession = sessionmaker(bind=eng)
        app.dependency_overrides[get_db] = lambda: TestSession()
        try:
            token, _ = _make_token(auth_env)
            r = TestClient(app).get(
                "/words/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200
            assert r.json() == {"id": 1, "username": "dou", "display_name": "小豆",
                                "role": "student"}
        finally:
            app.dependency_overrides.clear()

    def test_me_without_token_401(self, auth_env, monkeypatch):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.main import app
        from app.database import get_db

        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        TestSession = sessionmaker(bind=eng)
        app.dependency_overrides[get_db] = lambda: TestSession()
        try:
            r = TestClient(app).get("/words/api/auth/me")
            assert r.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestTTS:
    @pytest.mark.skipif(sys.platform != "darwin", reason="仅 macOS")
    def test_tts_generates_audio(self, auth_env):
        from fastapi.testclient import TestClient
        from app.main import app
        r = TestClient(app).get("/words/api/tts/chance.m4a")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/mp4"
        assert len(r.content) > 1000

    def test_tts_rejects_injection(self, auth_env):
        from fastapi.testclient import TestClient
        from app.main import app
        r = TestClient(app).get("/words/api/tts/%3B%20rm%20-rf.m4a")
        assert r.status_code in (400, 404)  # 白名单拦截


class TestFallbackLogin:
    def test_fallback_verify_and_issue_token(self, auth_env, monkeypatch):
        """错题本不可达时：bcrypt 直验 users 表 + 自签 token。"""
        from app import main as main_mod
        from passlib.context import CryptContext

        def unreachable(url, json=None, timeout=None):
            raise httpx.ConnectTimeout("down", request=httpx.Request("POST", url))

        monkeypatch.setattr(main_mod.httpx, "post", unreachable)
        # 给 dou 一个已知密码的 bcrypt 哈希
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from fastapi.testclient import TestClient
        from app.main import app
        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with eng.begin() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50), "
                              "password_hash VARCHAR(255), display_name VARCHAR(100), role VARCHAR(20))"))
            conn.execute(text("CREATE TABLE token_blacklist (id INTEGER PRIMARY KEY, jti VARCHAR(36) UNIQUE, expires_at DATETIME)"))
            conn.execute(text("INSERT INTO users VALUES (2, 'dou', :h, '小豆', 'student')"), {"h": ctx.hash("dou12345678")})
        from app import main as _m
        TestSession = sessionmaker(bind=eng)
        import app.database as _db
        monkeypatch.setattr(_db, "UserSessionLocal", TestSession)
        try:
            c = TestClient(app)
            r = c.post("/words/api/auth/login", json={"username": "dou", "password": "dou12345678"})
            assert r.status_code == 200
            assert r.json()["access_token"]
            assert r.json().get("_fallback") is True
            # 错误密码 → 401
            r2 = c.post("/words/api/auth/login", json={"username": "dou", "password": "nope"})
            assert r2.status_code == 401
            # 用 fallback token 能过 /auth/me
            r3 = c.get("/words/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
            assert r3.status_code == 200
            assert r3.json()["username"] == "dou"
        finally:
            app.dependency_overrides.clear()
