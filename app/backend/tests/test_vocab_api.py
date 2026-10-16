"""T3: 词库只读 API 测试（真实 vocabulary.db）。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


REAL_DB = Path(__file__).resolve().parent.parent.parent.parent / "output" / "vocabulary.db"
requires_vocab = pytest.mark.skipif(not REAL_DB.exists(), reason="词库未生成")


@requires_vocab
class TestWordEndpoints:
    def test_get_word_by_id(self, client):
        r = client.get("/words/api/words/V00520")
        assert r.status_code == 200
        assert r.json()["word"] == "chance"

    def test_get_word_404(self, client):
        assert client.get("/words/api/words/V99999").status_code == 404

    def test_units_list(self, client):
        r = client.get("/words/api/units")
        assert r.status_code == 200
        units = r.json()
        assert {"grade": "六", "semester": "上", "unit": "5"} in units

    def test_unit_words(self, client):
        r = client.get("/words/api/units/六/上/5")
        assert r.status_code == 200
        words = r.json()
        assert "amazing" in [w["word"] for w in words]
        assert all(any(tb["grade"] == "六" and tb["semester"] == "上" and tb["unit"] == "5"
                       for tb in w["textbook"]) for w in words)
