"""T2: 噪音过滤与区段识别。

区段边界由全书唯一出现的标题行定位（见 design.md §3）：
  一、考纲单词的基本用法  → words      (tag: 考纲)
  二、考纲词组的基本用法  → phrases    (tag: 考纲)
  第二单元                → level3     (tag: 三级词汇)
  第三单元                → jxjy       (tag: 学科教学基本要求)
  第四单元                → textbook   (tag: 教材)
  附录                    → appendix   (不入库)
第一单元标题之前的页面归为 front（版权/前言/目录，不入库）。
"""
from __future__ import annotations

import re

# 页脚/二维码噪音
_PAGE_NO_RE = re.compile(r"^\d{1,4}$")
_QR_NOISE = ("微信扫码", "听音频", "单词朗读音频", "词汇学习资料", "扫码获取")

_SECTION_HEADERS = [
    ("一、考纲单词的基本用法", "words", "考纲"),
    ("二、考纲词组的基本用法", "phrases", "考纲"),
    ("第二单元", "level3", "三级词汇"),
    ("第三单元", "jxjy", "学科教学基本要求"),
    ("第四单元", "textbook", "教材"),
    ("附录", "appendix", None),
]


def filter_noise(lines: list[dict]) -> list[dict]:
    out = []
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        if _PAGE_NO_RE.fullmatch(text):
            continue
        if any(noise in text for noise in _QR_NOISE):
            continue
        out.append({"y": line["y"], "text": text})
    return out


def detect_sections(pages: list[dict]) -> list[dict]:
    """按标题行把页面划入区段。返回按起始页排序的区段列表。"""
    marks = []  # (page, y, id, tag)
    for page in pages:
        for line in filter_noise(page["lines"]):
            text = line["text"]
            for header, sid, tag in _SECTION_HEADERS:
                if text.startswith(header) and "⋯" not in text and len(text) <= len(header) + 30:
                    marks.append((page["page"], line["y"], sid, tag))
                    break
    # 每类区段标题全书只出现一次（目录页的带 ⋯⋯ 行超长被排除）
    marks.sort()
    sections = []
    if marks and marks[0][2] != "front":
        first_start = marks[0][0]
        sections.append({"id": "front", "tag": None, "start_page": 1, "end_page": first_start - 1})
    for i, (pg, _y, sid, tag) in enumerate(marks):
        end = marks[i + 1][0] - 1 if i + 1 < len(marks) else pages[-1]["page"]
        sections.append({"id": sid, "tag": tag, "start_page": pg, "end_page": end})
    return sections


def page_to_section(page_number: int, sections: list[dict]) -> dict | None:
    for s in sections:
        if s["start_page"] <= page_number <= s["end_page"]:
            return s
    return None
