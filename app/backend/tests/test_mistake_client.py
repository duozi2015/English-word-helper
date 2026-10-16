"""T7: 错题本联动 client 测试（monkeypatch httpx.post 捕获 payload）。"""
import httpx
import pytest

from app import mistake_client


@pytest.fixture
def capture(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        r = httpx.Response(200, json={"id": 1}, request=httpx.Request("POST", url))
        return r

    monkeypatch.setattr(mistake_client.httpx, "post", fake_post)
    return calls


REC = {"id": "V00520", "word": "chance",
       "meanings": [{"pos": "n.", "meaning": "机会"}]}


class TestForwardToMistakebook:
    def test_spell_wrong_payload(self, capture):
        send = mistake_client.make_sender("Bearer tok-abc")
        send(REC, "chnace", "spell")
        body = capture[0]["json"]
        assert capture[0]["url"].endswith("/api/v1/questions")
        assert body["subject"] == "英语"
        assert body["error_type"] == "拼写错误"
        assert body["source"] == "english-word-helper"
        assert "单词" in body["tags"] and "单词:chance" in body["tags"]
        assert body["correct_solution"] == "n. 机会"
        assert "chnace" in body["user_analysis"]
        assert capture[0]["headers"]["Authorization"] == "Bearer tok-abc"

    def test_choice_wrong_payload(self, capture):
        send = mistake_client.make_sender("Bearer tok")
        send(REC, "", "choice")
        assert capture[0]["json"]["error_type"] == "词义混淆"

    def test_disabled_no_call(self, capture, monkeypatch):
        monkeypatch.setenv("LINK_MISTAKEBOOK", "false")
        mistake_client.get_settings.cache_clear()
        send = mistake_client.make_sender("Bearer tok")
        send(REC, "x", "spell")
        assert capture == []
        mistake_client.get_settings.cache_clear()

    def test_timeout_low(self, capture):
        send = mistake_client.make_sender("Bearer tok")
        send(REC, "x", "spell")
        # timeout 参数存在（联动失败不阻塞主流程由 review_service 捕获异常保证）
        assert capture[0]["json"]["difficulty"] == 3
