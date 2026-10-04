"""T10: JSONL + meta → SQLite 导出。

主表 vocabulary（一词一行，原始 JSON 全文保留）+ 展开子表（第二阶段查询友好）。
"""
from __future__ import annotations

import json
from pathlib import Path

_SCHEMA = """
CREATE TABLE vocabulary (
    id TEXT PRIMARY KEY,
    word TEXT NOT NULL,
    phonetic TEXT NOT NULL DEFAULT '',
    exam_level INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '[]',
    json TEXT NOT NULL
);
CREATE INDEX idx_vocabulary_word ON vocabulary(word);
CREATE TABLE meanings (
    id TEXT, pos TEXT, meaning TEXT
);
CREATE INDEX idx_meanings_id ON meanings(id);
CREATE TABLE word_forms (
    id TEXT, type TEXT, form TEXT, source TEXT
);
CREATE INDEX idx_word_forms_id ON word_forms(id);
CREATE TABLE related_words (
    id TEXT, word TEXT, pos TEXT, meaning TEXT, relation TEXT
);
CREATE INDEX idx_related_words_id ON related_words(id);
CREATE TABLE phrases (
    id TEXT, text TEXT, meaning TEXT
);
CREATE INDEX idx_phrases_id ON phrases(id);
CREATE TABLE proverbs (
    id TEXT, text TEXT, meaning TEXT
);
CREATE TABLE examples (
    id TEXT, en TEXT, zh TEXT, type TEXT
);
CREATE INDEX idx_examples_id ON examples(id);
CREATE TABLE usage_notes (
    id TEXT, note TEXT
);
CREATE TABLE teaching_notes (
    id TEXT, type TEXT, title TEXT, content TEXT
);
CREATE INDEX idx_teaching_notes_id ON teaching_notes(id);
CREATE TABLE textbook (
    id TEXT, grade TEXT, semester TEXT, unit TEXT
);
CREATE TABLE meta (
    id TEXT PRIMARY KEY, word TEXT, seq INTEGER, section TEXT,
    page INTEGER, original_phonetic TEXT, warnings TEXT
);
"""


def export_db(jsonl_path: str, db_path: str, meta: list[dict] | None = None) -> None:
    import sqlite3

    db = Path(db_path)
    if db.exists():
        db.unlink()  # 全量重建
    con = sqlite3.connect(db_path)
    con.executescript(_SCHEMA)
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            vid = rec["id"]
            con.execute(
                "INSERT INTO vocabulary VALUES (?,?,?,?,?,?)",
                (vid, rec["word"], rec["phonetic"], rec["exam_level"],
                 json.dumps(rec["tags"], ensure_ascii=False), line.strip()),
            )
            for m in rec["meanings"]:
                con.execute("INSERT INTO meanings VALUES (?,?,?)", (vid, m["pos"], m["meaning"]))
            for wf in rec["word_forms"]:
                con.execute("INSERT INTO word_forms VALUES (?,?,?,?)",
                            (vid, wf["type"], wf["form"], wf["source"]))
            for rw in rec["related_words"]:
                con.execute("INSERT INTO related_words VALUES (?,?,?,?,?)",
                            (vid, rw["word"], rw["pos"], rw["meaning"], rw["relation"]))
            for p in rec["phrases"]:
                con.execute("INSERT INTO phrases VALUES (?,?,?)", (vid, p["text"], p["meaning"]))
            for p in rec["proverbs"]:
                con.execute("INSERT INTO proverbs VALUES (?,?,?)", (vid, p["text"], p["meaning"]))
            for ex in rec["examples"]:
                con.execute("INSERT INTO examples VALUES (?,?,?,?)",
                            (vid, ex["en"], ex["zh"], ex["type"]))
            for u in rec["usage_notes"]:
                con.execute("INSERT INTO usage_notes VALUES (?,?)", (vid, u))
            for tn in rec["teaching_notes"]:
                con.execute("INSERT INTO teaching_notes VALUES (?,?,?,?)",
                            (vid, tn["type"], tn["title"], tn["content"]))
            for tb in rec["textbook"]:
                con.execute("INSERT INTO textbook VALUES (?,?,?,?)",
                            (vid, tb["grade"], tb["semester"], tb["unit"]))
    for m in (meta or []):
        con.execute(
            "INSERT INTO meta VALUES (?,?,?,?,?,?,?)",
            (m["id"], m["word"], m["seq"], m["section"], m["page"],
             m["original_phonetic"], json.dumps(m["warnings"], ensure_ascii=False)),
        )
    con.commit()
    con.close()
