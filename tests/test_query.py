"""query.py 测试 — 第二阶段数据库读取接口（fixture 库 + 真实库冒烟）。"""
import json
import sqlite3
from pathlib import Path

import pytest

from wordhelper.export_db import export_db
from wordhelper.query import VocabularyQuery

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
GOOD2 = {
    **GOOD, "id": "V00002", "word": "big", "exam_level": 3,
    "meanings": [{"pos": "adj.", "meaning": "大的"}],
    "word_forms": [], "related_words": [], "phrases": [], "examples": [],
    "usage_notes": [], "teaching_notes": [], "textbook": [],
}
META = [
    {"id": "V00001", "word": "accident", "seq": 7, "section": "words",
     "page": 10, "original_phonetic": "/?ksidont/", "warnings": []},
    {"id": "V00002", "word": "big", "seq": 8, "section": "words",
     "page": 10, "original_phonetic": "", "warnings": []},
]


@pytest.fixture
def q(tmp_path):
    jsonl = tmp_path / "v.jsonl"
    jsonl.write_text(
        json.dumps(GOOD, ensure_ascii=False) + "\n" + json.dumps(GOOD2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    db = tmp_path / "v.db"
    export_db(str(jsonl), str(db), META)
    return VocabularyQuery(str(db))


class TestWordLookup:
    def test_get_word_full_record(self, q):
        rec = q.get_word("accident")
        assert rec["id"] == "V00001"
        assert rec["meanings"] == GOOD["meanings"]
        assert rec["phrases"] == GOOD["phrases"]

    def test_get_word_missing_returns_none(self, q):
        assert q.get_word("zzz") is None

    def test_meanings(self, q):
        assert q.meanings("accident") == [("n.", "事故；意外")]

    def test_examples(self, q):
        ex = q.examples("accident")
        assert ex == [{"en": "It happened by accident.", "zh": "偶然发生的。", "type": "general"}]

    def test_phrases_and_forms(self, q):
        assert q.phrases("accident") == [("by accident", "偶然地")]
        assert q.word_forms("accident") == [("plural", "accidents", "ai")]

    def test_teaching_notes(self, q):
        tn = q.teaching_notes("accident")
        assert tn[0]["type"] == "usage"

    def test_meta(self, q):
        m = q.meta("accident")
        assert m["original_phonetic"] == "/?ksidont/"


class TestBrowse:
    def test_by_textbook(self, q):
        words = q.by_textbook("七", "下", "4")
        assert [w["word"] for w in words] == ["accident"]

    def test_by_exam_level_min(self, q):
        words = [w["word"] for w in q.by_exam_level(min_level=2)]
        assert words == ["big"]

    def test_random_words(self, q):
        assert len(q.random_words(1)) == 1

    def test_search_prefix(self, q):
        words = [w["word"] for w in q.search("acc")]
        assert "accident" in words

    def test_stats(self, q):
        s = q.stats()
        assert s["total"] == 2
        assert s["by_section"]["words"] == 2


class TestRealDbSmoke:
    REAL = Path(__file__).parent.parent / "output" / "vocabulary.db"

    @pytest.mark.skipif(not REAL.exists(), reason="真实库未生成")
    def test_real_db(self):
        q = VocabularyQuery(str(self.REAL))
        assert q.stats()["total"] == 2940
        rec = q.get_word("chance")
        assert rec is not None and rec["exam_level"] >= 0
