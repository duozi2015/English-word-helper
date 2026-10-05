"""第二阶段数据库读取接口。

用法：
    from wordhelper.query import VocabularyQuery
    q = VocabularyQuery("output/vocabulary.db")
    rec = q.get_word("chance")          # 完整记录（dict）
    q.meanings("chance")                # [("n.", "机会")]
    q.by_textbook("六", "上", "5")       # 某单元词表

注意：同一 word 可能在多个区段出现（如 be 同时在考纲动词区与词组区），
word 类查询返回第一条；需要全部时用 get_word_all()。
"""
from __future__ import annotations

import json
import sqlite3


class VocabularyQuery:
    def __init__(self, db_path: str):
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row

    def close(self) -> None:
        self.con.close()

    # ---------- 完整记录 ----------

    def get_word_all(self, word: str) -> list[dict]:
        rows = self.con.execute(
            "SELECT json FROM vocabulary WHERE word = ? ORDER BY id", (word,)
        ).fetchall()
        return [json.loads(r["json"]) for r in rows]

    def get_word(self, word: str) -> dict | None:
        recs = self.get_word_all(word)
        return recs[0] if recs else None

    def get_by_id(self, vid: str) -> dict | None:
        row = self.con.execute(
            "SELECT json FROM vocabulary WHERE id = ?", (vid,)
        ).fetchone()
        return json.loads(row["json"]) if row else None

    # ---------- 分字段查询（word → 第一条记录） ----------

    def _first_id(self, word: str) -> str | None:
        row = self.con.execute(
            "SELECT id FROM vocabulary WHERE word = ? ORDER BY id LIMIT 1", (word,)
        ).fetchone()
        return row["id"] if row else None

    def meanings(self, word: str) -> list[tuple[str, str]]:
        vid = self._first_id(word)
        if not vid:
            return []
        return [(r["pos"], r["meaning"]) for r in self.con.execute(
            "SELECT pos, meaning FROM meanings WHERE id = ?", (vid,))]

    def word_forms(self, word: str) -> list[tuple[str, str, str]]:
        """返回 (type, form, source)。"""
        vid = self._first_id(word)
        if not vid:
            return []
        return [(r["type"], r["form"], r["source"]) for r in self.con.execute(
            "SELECT type, form, source FROM word_forms WHERE id = ?", (vid,))]

    def related_words(self, word: str) -> list[dict]:
        vid = self._first_id(word)
        if not vid:
            return []
        return [dict(r) for r in self.con.execute(
            "SELECT word, pos, meaning, relation FROM related_words WHERE id = ?", (vid,))]

    def phrases(self, word: str) -> list[tuple[str, str]]:
        vid = self._first_id(word)
        if not vid:
            return []
        return [(r["text"], r["meaning"]) for r in self.con.execute(
            "SELECT text, meaning FROM phrases WHERE id = ?", (vid,))]

    def examples(self, word: str) -> list[dict]:
        vid = self._first_id(word)
        if not vid:
            return []
        return [dict(r) for r in self.con.execute(
            "SELECT en, zh, type FROM examples WHERE id = ?", (vid,))]

    def teaching_notes(self, word: str) -> list[dict]:
        vid = self._first_id(word)
        if not vid:
            return []
        return [dict(r) for r in self.con.execute(
            "SELECT type, title, content FROM teaching_notes WHERE id = ?", (vid,))]

    def textbook(self, word: str) -> list[dict]:
        vid = self._first_id(word)
        if not vid:
            return []
        return [dict(r) for r in self.con.execute(
            "SELECT grade, semester, unit FROM textbook WHERE id = ?", (vid,))]

    def meta(self, word: str) -> dict | None:
        vid = self._first_id(word)
        if not vid:
            return None
        row = self.con.execute("SELECT * FROM meta WHERE id = ?", (vid,)).fetchone()
        return dict(row) if row else None

    # ---------- 浏览与筛选 ----------

    def by_textbook(self, grade: str, semester: str | None = None,
                    unit: str | None = None) -> list[dict]:
        sql = ("SELECT v.* FROM vocabulary v JOIN textbook t ON t.id = v.id "
               "WHERE t.grade = ?")
        args: list = [grade]
        if semester:
            sql += " AND t.semester = ?"
            args.append(semester)
        if unit:
            sql += " AND t.unit = ?"
            args.append(unit)
        sql += " ORDER BY v.id"
        rows = self.con.execute(sql, args).fetchall()
        out, seen = [], set()
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(json.loads(r["json"]))
        return out

    def by_exam_level(self, min_level: int = 0, max_level: int = 3) -> list[dict]:
        rows = self.con.execute(
            "SELECT json FROM vocabulary WHERE exam_level BETWEEN ? AND ? ORDER BY id",
            (min_level, max_level)).fetchall()
        return [json.loads(r["json"]) for r in rows]

    def search(self, prefix: str, limit: int = 50) -> list[dict]:
        rows = self.con.execute(
            "SELECT json FROM vocabulary WHERE word LIKE ? ORDER BY word LIMIT ?",
            (prefix + "%", limit)).fetchall()
        return [json.loads(r["json"]) for r in rows]

    def random_words(self, n: int, min_level: int = 0) -> list[dict]:
        rows = self.con.execute(
            "SELECT json FROM vocabulary WHERE exam_level >= ? ORDER BY RANDOM() LIMIT ?",
            (min_level, n)).fetchall()
        return [json.loads(r["json"]) for r in rows]

    def stats(self) -> dict:
        total = self.con.execute("SELECT COUNT(*) c FROM vocabulary").fetchone()["c"]
        by_section = {r["section"]: r["c"] for r in self.con.execute(
            "SELECT section, COUNT(*) c FROM meta GROUP BY section")}
        return {"total": total, "by_section": by_section}
