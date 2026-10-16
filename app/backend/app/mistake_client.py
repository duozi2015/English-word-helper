"""错题本联动：错词 → POST /api/v1/questions（契约见 design2.md §6）。

注意：需要学生本人的 Authorization 头（user_id 由错题本从 JWT 取）。
"""
from __future__ import annotations

import httpx

from app.config import get_settings


def make_sender(auth_header: str):
    """返回 f(word_rec, wrong_answer, mode)；异常由调用方（review_service）吞掉。"""
    settings = get_settings()

    def send(rec: dict, wrong_answer: str, mode: str) -> None:
        if not settings.LINK_MISTAKEBOOK:
            return
        meanings = "；".join(
            f"{m['pos']} {m['meaning']}".strip() for m in rec["meanings"]
        ) or rec["word"]
        if mode == "spell":
            error_type = "拼写错误"
            content = f"{rec['word']} — ______（看中文拼单词）"
        else:
            error_type = "词义混淆"
            content = f"{rec['word']} — 词义辨析（选择题答错）"
        payload = {
            "subject": "英语",
            "question_content": content,
            "correct_solution": meanings,
            "user_analysis": f"你的答案：{wrong_answer}" if wrong_answer else "",
            "error_type": error_type,
            "difficulty": 3,
            "source": "english-word-helper",
            "tags": ["单词", "考纲词汇", f"单词:{rec['word']}"],
        }
        httpx.post(
            f"{settings.MISTAKEBOOK_API}/api/v1/questions",
            json=payload,
            headers={"Authorization": auth_header},
            timeout=3,
        )

    return send
