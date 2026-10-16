"""T0: 健康检查 + 应用骨架测试。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_app_title(self, client):
        assert client.get("/health").json()["app"] == "english-word-app"
