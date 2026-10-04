"""T10: export_db.py 测试 — JSONL → SQLite。"""
import json
import sqlite3

from wordhelper.export_db import export_db

GOOD = {
    "id": "V00001", "word": "accident", "phonetic": "",
    "meanings": [{"pos": "n.", "meaning": "事故；意外"}],
    "word_forms": [{"type": "plural", "form": "accidents", "source": "ai"}],
    "related_words": [{"word": "accidental", "pos": "adj.", "meaning": "偶然的",
                       "relation": "词形拓展"}],
    "phrases": [{"text": "by accident", "meaning": "偶然地"}],
    "collocations": [], "proverbs": [],
    "examples": [{"en": "It happened by accident.", "zh": "偶然发生的。", "type": "general"}],
    "usage_notes": ["介词用 by"],
    "teaching_notes": [{"type": "usage", "title": "", "content": "常考"}],
    "tags": ["考纲"], "exam_level": 1,
    "textbook": [{"grade": "七", "semester": "下", "unit": "4"}],
}

META = [{"id": "V00001", "word": "accident", "seq": 7, "section": "words",
         "page": 10, "original_phonetic": "/?ksidont/", "warnings": []}]


class TestExportDb:
    def test_roundtrip(self, tmp_path):
        jsonl = tmp_path / "vocabulary.jsonl"
        jsonl.write_text(json.dumps(GOOD, ensure_ascii=False) + "\n", encoding="utf-8")
        db = tmp_path / "vocabulary.db"
        export_db(str(jsonl), str(db), META)
        con = sqlite3.connect(db)
        assert con.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0] == 1
        row = con.execute("SELECT word, exam_level FROM vocabulary").fetchone()
        assert row == ("accident", 1)
        assert con.execute("SELECT meaning FROM meanings WHERE id='V00001'").fetchone()[0] == "事故；意外"
        assert con.execute("SELECT form FROM word_forms WHERE type='plural'").fetchone()[0] == "accidents"
        assert con.execute("SELECT meaning FROM related_words").fetchone()[0] == "偶然的"
        assert con.execute("SELECT text FROM phrases").fetchone()[0] == "by accident"
        assert con.execute("SELECT en FROM examples").fetchone()[0].startswith("It happened")
        assert con.execute("SELECT note FROM usage_notes").fetchone()[0] == "介词用 by"
        assert con.execute("SELECT type FROM teaching_notes").fetchone()[0] == "usage"
        assert con.execute("SELECT grade FROM textbook").fetchone()[0] == "七"
        assert con.execute("SELECT original_phonetic FROM meta").fetchone()[0] == "/?ksidont/"

    def test_lookup_by_word(self, tmp_path):
        jsonl = tmp_path / "vocabulary.jsonl"
        jsonl.write_text(json.dumps(GOOD, ensure_ascii=False) + "\n", encoding="utf-8")
        db = tmp_path / "vocabulary.db"
        export_db(str(jsonl), str(db), META)
        con = sqlite3.connect(db)
        assert con.execute("SELECT id FROM vocabulary WHERE word='accident'").fetchone()[0] == "V00001"
