"""词库只读访问层（vendor 自第一阶段 wordhelper/query.py，SQLite 只读）。"""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache

from app.config import get_settings


@lru_cache
def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(get_settings().VOCAB_DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def get_word_all(word: str) -> list[dict]:
    rows = _connect().execute(
        "SELECT json FROM vocabulary WHERE word = ? ORDER BY id", (word,)
    ).fetchall()
    return [json.loads(r["json"]) for r in rows]


def get_word(word: str) -> dict | None:
    recs = get_word_all(word)
    return recs[0] if recs else None


def get_by_id(vid: str) -> dict | None:
    row = _connect().execute(
        "SELECT json FROM vocabulary WHERE id = ?", (vid,)
    ).fetchone()
    return json.loads(row["json"]) if row else None


def units() -> list[dict]:
    """教材单元列表（去重排序）。"""
    rows = _connect().execute(
        "SELECT DISTINCT grade, semester, unit FROM textbook"
    ).fetchall()
    order = {"六": 0, "七": 1, "八": 2, "": 9}
    out = [
        {"grade": r["grade"], "semester": r["semester"], "unit": r["unit"]}
        for r in rows if r["grade"] and r["unit"]
    ]
    out.sort(key=lambda x: (order.get(x["grade"], 9), x["semester"], int(x["unit"])))
    return out


def unit_words(grade: str, semester: str, unit: str) -> list[dict]:
    """单元词表（textbook 子表无词库主键，全表扫描 JSON；2940 行量小可接受）。"""
    words = []
    for wj in _connect().execute("SELECT id, json FROM vocabulary ORDER BY id"):
        rec = json.loads(wj["json"])
        for tb in rec["textbook"]:
            if tb["grade"] == grade and tb["semester"] == semester and tb["unit"] == unit:
                words.append(rec)
                break
    return words


def word_count() -> int:
    return _connect().execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]


def iter_words_ordered() -> list[dict]:
    """全部词条，★ 数降序（高频优先）、同星按 id。"""
    rows = _connect().execute(
        "SELECT json FROM vocabulary ORDER BY exam_level DESC, id"
    ).fetchall()
    return [json.loads(r["json"]) for r in rows]


def choice_distractors(word_id: str, pos: str, n: int = 3) -> list[str]:
    """同词性随机干扰释义（去重、去正确项；不足时放宽词性）。"""
    import random as _random
    con = _connect()
    correct = get_by_id(word_id)
    correct_meanings = {m["meaning"] for m in correct["meanings"]} if correct else set()
    out: list[str] = []
    for scope in (f"AND meanings LIKE ?", ""):
        if scope:
            rows = con.execute(
                "SELECT json FROM vocabulary WHERE json LIKE ? AND id != ? ORDER BY RANDOM() LIMIT ?",
                (f'%"{pos}"%', word_id, 50)).fetchall()
        else:
            rows = con.execute(
                "SELECT json FROM vocabulary WHERE id != ? ORDER BY RANDOM() LIMIT ?",
                (word_id, 50)).fetchall()
        for r in rows:
            rec = json.loads(r["json"])
            for m in rec["meanings"]:
                if m["meaning"] not in correct_meanings and m["meaning"] not in out:
                    out.append(m["meaning"])
            if len(out) >= n:
                break
        if len(out) >= n:
            break
    return out[:n]
