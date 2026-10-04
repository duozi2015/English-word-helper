"""T9: validate.py 测试 — Schema 校验与一致性质检。"""
import json
from pathlib import Path

from wordhelper.validate import validate_schema, consistency_report

SCHEMA = Path(__file__).parent.parent / "docs" / "上海初中英语AI学习产品_词汇JSONSchema_V1.2.json"

GOOD = {
    "id": "V00001", "word": "accident", "phonetic": "",
    "meanings": [{"pos": "n.", "meaning": "事故；意外"}],
    "word_forms": [], "related_words": [],
    "phrases": [{"text": "by accident", "meaning": "偶然地"}],
    "collocations": [], "proverbs": [],
    "examples": [{"en": "It happened by accident.", "zh": "偶然发生的。", "type": "general"}],
    "usage_notes": [], "teaching_notes": [], "tags": ["考纲"],
    "exam_level": 1, "textbook": [],
}


class TestValidateSchema:
    def test_good_record_passes(self):
        errors = validate_schema([GOOD], str(SCHEMA))
        assert errors == []

    def test_missing_field_fails(self):
        bad = {k: v for k, v in GOOD.items() if k != "proverbs"}
        errors = validate_schema([bad], str(SCHEMA))
        assert len(errors) == 1
        assert "proverbs" in errors[0]

    def test_bad_enum_fails(self):
        bad = dict(GOOD, id="X999")
        errors = validate_schema([bad], str(SCHEMA))
        assert len(errors) == 1

    def test_extra_field_fails(self):
        bad = dict(GOOD, _secret=1)
        errors = validate_schema([bad], str(SCHEMA))
        assert len(errors) == 1


class TestConsistencyReport:
    def test_structure(self):
        meta = [
            {"id": "V00001", "word": "a", "seq": 1, "section": "words",
             "page": 8, "original_phonetic": "", "warnings": []},
            {"id": "V00002", "word": "a", "seq": 3, "section": "words",
             "page": 8, "original_phonetic": "", "warnings": ["序号不连续: 1 -> 3"]},
        ]
        records = [dict(GOOD, id="V00001", word="a"), dict(GOOD, id="V00002", word="a")]
        report = consistency_report(records, meta)
        assert "duplicate_words" in report
        assert report["total"] == 2
        assert any(d["word"] == "a" for d in report["duplicate_words"])

    def test_seq_gaps_collected(self):
        meta = [
            {"id": "V00001", "word": "a", "seq": 1, "section": "words",
             "page": 8, "original_phonetic": "", "warnings": []},
            {"id": "V00002", "word": "b", "seq": 3, "section": "words",
             "page": 8, "original_phonetic": "", "warnings": ["序号不连续: 1 -> 3"]},
        ]
        records = [dict(GOOD, id="V00001", word="a"), dict(GOOD, id="V00002", word="b")]
        report = consistency_report(records, meta)
        assert len(report["seq_gaps"]) == 1
