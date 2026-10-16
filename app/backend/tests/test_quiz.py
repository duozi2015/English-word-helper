"""T10: 选择题干扰项测试（真实词库）。"""
from pathlib import Path

import pytest

from app import vocab_store

requires_vocab = pytest.mark.skipif(
    not (Path(__file__).resolve().parent.parent.parent.parent / "output/vocabulary.db").exists(),
    reason="词库未生成")


@requires_vocab
class TestChoiceDistractors:
    def test_three_distinct_distractors(self):
        out = vocab_store.choice_distractors("V00520", "n.", 3)
        assert len(out) == 3
        assert len(set(out)) == 3
        assert "机会" not in out

    def test_fallback_relaxes_pos(self):
        """生僻词性也能凑满 3 个。"""
        out = vocab_store.choice_distractors("V00520", "interj.", 3)
        assert len(out) == 3

    def test_quiz_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app
        r = TestClient(app).get("/words/api/quiz/choice/V00520")
        assert r.status_code == 200
        data = r.json()
        assert data["word"] == "chance"
        assert data["correct"] == "机会"
        assert len(data["options"]) == 4
        assert data["correct"] in data["options"]
        assert len(set(data["options"])) == 4
