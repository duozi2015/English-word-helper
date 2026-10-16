

class TestProxyLogin:
    def test_login_passthrough(self, monkeypatch):
        from app import main as main_mod

        calls = {}

        def fake_post(url, json=None, timeout=None):
            calls["url"] = url
            calls["json"] = json
            return httpx.Response(200, json={"access_token": "tok", "refresh_token": "rtok",
                                             "token_type": "bearer"},
                                  request=httpx.Request("POST", url))

        monkeypatch.setattr(main_mod.httpx, "post", fake_post)
        c = TestClient(app)
        r = c.post("/words/api/auth/login", json={"username": "dou", "password": "x"})
        assert r.status_code == 200
        assert r.json()["access_token"] == "tok"
        assert calls["url"].endswith("/api/v1/auth/login")

    def test_login_upstream_failure(self, monkeypatch):
        from app import main as main_mod

        def fake_post(url, json=None, timeout=None):
            return httpx.Response(401, json={"detail": "密码错误"},
                                  request=httpx.Request("POST", url))

        monkeypatch.setattr(main_mod.httpx, "post", fake_post)
        c = TestClient(app)
        assert c.post("/words/api/auth/login", json={"username": "dou", "password": "x"}).status_code == 401


class TestTTS:
    @pytest.mark.skipif(sys.platform != "darwin", reason="仅 macOS")
    def test_tts_generates_audio(self, auth_env):
        import pathlib
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


class TestProxyLoginRobustness:
    def test_non_json_upstream_502(self, monkeypatch):
        from app import main as main_mod

        def fake_post(url, json=None, timeout=None):
            return httpx.Response(200, text="<html>nginx</html>",
                                  request=httpx.Request("POST", url))

        monkeypatch.setattr(main_mod.httpx, "post", fake_post)
        c = TestClient(app)
        assert c.post("/words/api/auth/login", json={"username": "dou", "password": "x"}).status_code == 502

    def test_timeout_502(self, monkeypatch):
        from app import main as main_mod

        def fake_post(url, json=None, timeout=None):
            raise httpx.ConnectTimeout("timeout", request=httpx.Request("POST", url))

        monkeypatch.setattr(main_mod.httpx, "post", fake_post)
        c = TestClient(app)
        assert c.post("/words/api/auth/login", json={"username": "dou", "password": "x"}).status_code == 502
