

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
