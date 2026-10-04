"""T2: segment.py 测试 — 噪音过滤与区段识别。"""
import json
from pathlib import Path

import pytest

from wordhelper.segment import detect_sections, filter_noise

FIXTURES = Path(__file__).parent / "fixtures"
sample_pages = json.load(open(FIXTURES / "sample_pages.json"))


def _page(pg):
    return [p for p in sample_pages if p["page"] == pg][0]


class TestFilterNoise:
    def test_removes_page_number_line(self):
        lines = [{"y": 100, "text": "265.*chance /tSO:ns/ n.机会"},
                 {"y": 701, "text": "44"}]
        out = filter_noise(lines)
        assert [l["text"] for l in out] == ["265.*chance /tSO:ns/ n.机会"]

    def test_keeps_entry_starting_with_number(self):
        """词条行以数字开头（序号），不能误删。"""
        lines = [{"y": 100, "text": "265.*chance /tSO:ns/ n.机会"}]
        assert len(filter_noise(lines)) == 1

    def test_removes_qr_audio_noise(self):
        lines = [{"y": 50, "text": "微信扫码获取"},
                 {"y": 60, "text": "听音频，背单词"},
                 {"y": 70, "text": "单词朗读音频"},
                 {"y": 80, "text": "词汇学习资料"},
                 {"y": 100, "text": "?265.*chance n.机会"}]
        out = filter_noise(lines)
        assert [l["text"] for l in out] == ["?265.*chance n.机会"]

    def test_removes_empty_and_whitespace(self):
        lines = [{"y": 10, "text": ""},
                 {"y": 20, "text": "   "},
                 {"y": 30, "text": "chance"}]
        assert [l["text"] for l in filter_noise(lines)] == ["chance"]


class TestDetectSections:
    def test_structure(self):
        sections = detect_sections(sample_pages)
        # 每个区段: {id, tag, start_page, end_page}
        ids = [s["id"] for s in sections]
        assert ids == ["front", "words", "phrases", "level3", "jxjy", "textbook", "appendix"]

    def test_page_ranges(self):
        sections = {s["id"]: s for s in detect_sections(sample_pages)}
        # fixture 只含抽样页；words 应从 第8页 开始
        assert sections["words"]["start_page"] == 8
        # 前言(front)结束于第一单元之前
        assert sections["front"]["end_page"] < sections["words"]["start_page"]

    def test_tags(self):
        sections = {s["id"]: s for s in detect_sections(sample_pages)}
        assert sections["words"]["tag"] == "考纲"
        assert sections["phrases"]["tag"] == "考纲"
        assert sections["level3"]["tag"] == "三级词汇"
        assert sections["jxjy"]["tag"] == "学科教学基本要求"
        assert sections["textbook"]["tag"] == "教材"
