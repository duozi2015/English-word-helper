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
    """按标题行把页面划入区段。返回按起始页排序的区段列表。

    另含 bounds: [(page, y, id, tag)] 行级边界，供 split_book 使用。
    """
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
    sections[-1]["bounds"] = [(pg, y, sid, tag) for pg, y, sid, tag in marks]
    return sections


def _line_section(page_number: int, y: float, bounds: list[tuple]) -> tuple[str, str | None]:
    """返回该行所属的 (section_id, tag)；标题行之前的行属于上一个区段。"""
    sid, tag = "front", None
    for pg, by, bid, btag in bounds:
        if (page_number, y) >= (pg, by):
            sid, tag = bid, btag
        else:
            break
    return sid, tag


def split_book(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    """行级分区 + 词条切分。返回 (entries, sections)。"""
    sections = detect_sections(pages)
    bounds = sections[-1]["bounds"]
    by_section: dict[str, list] = {}
    page_of: dict[str, int] = {}
    for page in pages:
        for line in filter_noise(page["lines"]):
            sid, _tag = _line_section(page["page"], line["y"], bounds)
            if sid in ("front", "appendix"):
                continue
            # 单个大写字母为章节水印
            if _WATERMARK_RE.match(line["text"]):
                continue
            by_section.setdefault(sid, []).append({"y": line["y"], "text": line["text"], "page": page["page"]})
            page_of.setdefault(sid, page["page"])
    entries = []
    for sid in ("words", "phrases", "level3", "jxjy", "textbook"):
        lines = by_section.get(sid, [])
        entries += split_entries(lines, sid, page_of.get(sid, 0))
    return entries, sections


def page_to_section(page_number: int, sections: list[dict]) -> dict | None:
    for s in sections:
        if s["start_page"] <= page_number <= s["end_page"]:
            return s
    return None


# 词条起点：可选音频标记?(与数字间可有空格)，1-4位序号，点号，后随英文词形/星标
_ENTRY_RE = re.compile(r"^[A-Z]?\??\s*(\d{1,4})\.\s*(?=[A-Za-z*?])(?!\d)\s*(.*)$")
_WATERMARK_RE = re.compile(r"^[A-Z]$")


def split_entries(lines: list[dict], section: str, start_page: int) -> list[dict]:
    """把一个区段内的过滤后行按词条起点切分。

    返回 [{section, seq, start_page, text, warnings}]；
    序号跳号/重复时在该词条的 warnings 中记录。
    """
    entries = []
    current = None
    for line in lines:
        text = line["text"]
        m = _ENTRY_RE.match(text)
        if m:
            seq = int(m.group(1))
            warnings = []
            if current is not None and seq != current["seq"] + 1:
                warnings.append(f"序号不连续: {current['seq']} -> {seq}")
            current = {
                "section": section,
                "seq": seq,
                "start_page": line.get("page", start_page),
                "text": text,
                "warnings": warnings,
            }
            entries.append(current)
        elif current is not None and not _WATERMARK_RE.match(text):
            current["text"] += "\n" + text
    return entries
