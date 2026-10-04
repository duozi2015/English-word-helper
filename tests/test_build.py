"""T8: build.py 测试 — 组装 Vocabulary 记录与 id 分配。"""
from wordhelper.build import build_records

ENTRIES = [
    {"section": "words", "seq": 2, "start_page": 10,
     "text": "? 2.*busy/'bizi/ adj.忙的；繁忙的"},
    {"section": "words", "seq": 1, "seq_ok": True, "start_page": 8,
     "text": "? 1.*ability①/'brl?ti/(复abilities) n.能力，才能，本领"},
    {"section": "phrases", "seq": 1, "start_page": 271,
     "text": "1.*ask for要，请求"},
]


class TestBuildRecords:
    def setup_method(self):
        self.records, self.meta = build_records(ENTRIES)

    def test_schema_fields_exact(self):
        """记录字段与 Schema 完全一致（无多余字段）。"""
        expected = {"id", "word", "phonetic", "meanings", "word_forms",
                    "related_words", "phrases", "collocations", "proverbs",
                    "examples", "usage_notes", "teaching_notes", "tags",
                    "exam_level", "textbook"}
        assert set(self.records[0].keys()) == expected

    def test_id_sorted_by_word(self):
        """id 按 word 字典序分配。"""
        words = [r["word"] for r in self.records]
        assert words == sorted(words)
        assert [r["id"] for r in self.records] == ["V00001", "V00002", "V00003"]

    def test_meta_keeps_source_info(self):
        """seq/section/page/original_phonetic 保存在 meta。"""
        by_word = {m["word"]: m for m in meta_list(self.meta)}
        assert by_word["busy"]["section"] == "words"
        assert by_word["busy"]["original_phonetic"] == "/'bizi/"

    def test_phonetic_empty_debt(self):
        """音标为技术债务：phonetic 置空。"""
        assert all(r["phonetic"] == "" for r in self.records)

    def test_word_forms_completed(self):
        rec = next(r for r in self.records if r["word"] == "busy")
        types = {f["type"] for f in rec["word_forms"]}
        assert "comparative" in types


def meta_list(meta):
    if isinstance(meta, dict):
        return [dict(v, id=k) for k, v in meta.items()]
    return meta
