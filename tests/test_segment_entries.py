"""T3: segment.py 词条切分测试 — 用真实文本行做 fixture。"""
from wordhelper.segment import split_entries


def _lines(*texts):
    return [{"y": float(i * 10), "text": t} for i, t in enumerate(texts)]


class TestSplitEntries:
    def test_basic_split(self):
        lines = _lines(
            "?265.*chance /t?a:ns/ n.机会",
            "G7上U2 We should improve ourselves.",
            "我们应该抓住每一个机会。",
            "?266.***change /tfernd?/v.改变",
            "n.零钱；找头",
        )
        entries = split_entries(lines, section="words", start_page=51)
        assert len(entries) == 2
        assert entries[0]["seq"] == 265
        assert entries[1]["seq"] == 266

    def test_optional_q_prefix_ignored(self):
        """? 前缀（音频标记）可有可无，不影响识别。"""
        lines = _lines("267.***changeable adj.易变的")
        entries = split_entries(lines, section="words", start_page=1)
        assert entries[0]["seq"] == 267

    def test_entry_spans_pages(self):
        """词条跨页：下一页噪音已滤除，续行并入当前词条。"""
        lines = _lines(
            "?603.fit/fit/v.适合",
            "Do you have any ready-made clothes?",
            "你有适合我穿的成衣吗?",
        )
        entries = split_entries(lines, section="words", start_page=101)
        assert len(entries) == 1
        assert "ready-made" in entries[0]["text"]

    def test_watermark_letter_skipped(self):
        """单个大写字母是章节水印，不是内容。"""
        lines = _lines("?266.***change v.改变", "C", "G6下U6", "n.零钱")
        entries = split_entries(lines, section="words", start_page=51)
        assert len(entries) == 1
        assert "G6下U6" in entries[0]["text"]
        assert "\nC\n" not in entries[0]["text"]

    def test_header_lines_before_first_entry_skipped(self):
        lines = _lines("第一单元", "一、考纲单词的基本用法", "A", "?1.*a /e?/ art.一(个)")
        entries = split_entries(lines, section="words", start_page=8)
        assert len(entries) == 1
        assert entries[0]["seq"] == 1

    def test_text_and_meta(self):
        lines = _lines("?265.*chance /t?a:ns/ n.机会", "我们应该抓住每一个机会。")
        e = split_entries(lines, section="words", start_page=51)[0]
        assert e["section"] == "words"
        assert e["start_page"] == 51
        assert e["text"].startswith("?265.*chance")

    def test_pure_number_line_not_entry(self):
        """纯数字行（页码残留）不能成为词条起点。"""
        lines = _lines("?265.*chance n.机会", "44", "我们应该抓住每一个机会。")
        entries = split_entries(lines, section="words", start_page=51)
        assert len(entries) == 1

    def test_sequence_continuity_warnings(self):
        """序号跳号产出 warnings。"""
        lines = _lines("265.*chance n.机会", "267.***changeable adj.易变的")
        entries = split_entries(lines, section="words", start_page=1)
        assert any("265 -> 267" in w for w in entries[1]["warnings"])
