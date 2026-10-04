"""T4/T5: 词条解析 — 词头行、标记段、例句配对。

解析策略（design.md §4）：
1. 词头行先定位 word 边界（ASCII 词形字符）；
2. 在词形之后找第一条「词性链」（n./v./adj./n.&v./abbr: 等），
   词性与词形之间的区间内解析音标 /.../ 与括号内容（复X → plural，
   动词括号组 → 过去式/过去分词等，source=document）；
3. 词性链之后的文本按词性链切段得到 meanings。
"""
from __future__ import annotations

import re

# 词条前缀：可选水印字母/音频标记?、序号、星标
_HEAD_RE = re.compile(r"^[A-Z]?\??\s*\d{1,4}\.\s*")
_STARS_RE = re.compile(r"^(\*{0,3})\s*(.*)$")
# word：ASCII 词形字符（字母开头）；在 / ( [ " ? ! 或 空格后的重音符' 处停止
_WORD_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9 .,'()&-]*?(?=/|\(|\[|\"|\?|!|(?<=\s)[''‘`ˈ]|[^\x00-\x7F]|$)"
)
# 词性链：n. / v. / n.&v. / n.& num. / abbr: 等（不在英文单词内部）
_POS_CHAIN_RE = re.compile(
    r"(?<![A-Za-z])((?:(?:n|v|adj|adv|prep|pron|conj|num|int|interj|art|aux|abbr)[ ]?\.[ ]?(?:&[ ]?)?)+|abbr[:：])"
)
_CJK = r"一-鿿　-〿＀-￯⋯"
_UNIT_RE = re.compile(r"\(U(\d+)\)")


def _strip_prefix(text: str) -> str:
    m = _HEAD_RE.match(text)
    rest = text[m.end():] if m else text
    stars = _STARS_RE.match(rest)
    return stars.group(2), len(stars.group(1))


def _find_pos_start(rest: str, search_from: int) -> tuple[int, str] | None:
    """找词形之后、括号深度为 0 的第一条词性链。"""
    depth = 0
    for i in range(search_from, len(rest)):
        ch = rest[i]
        if ch in "(（[":
            depth += 1
        elif ch in ")）]":
            depth = max(0, depth - 1)
        elif depth == 0:
            m = _POS_CHAIN_RE.match(rest, i)
            if m:
                return i, m.group(1)
    return None


def _clean_phonetic(content: str) -> str:
    """音标内容截断：到 CJK/中文标点/括号为止，去首尾空白。"""
    m = re.match(r"[^" + _CJK + r"()（）]*", content)
    return m.group(0).strip()


def parse_head(text: str) -> dict:
    word, phonetic, word_forms, meanings = "", "", [], []
    units = []
    rest, exam_level = _strip_prefix(text)

    m = _WORD_RE.match(rest)
    word = m.group(0).strip() if m else ""
    search_from = m.end() if m else 0

    pos = _find_pos_start(rest, search_from)
    pos_start = pos[0] if pos else len(rest)
    zone = rest[search_from:pos_start]

    # --- 音标 ---
    z = zone.lstrip()
    if z[:1] in ('/', '"'):
        # 引号开音标为 OCR 把 / 误识为 "
        content = z[1:]
        end = content.find("/")
        if end >= 0:
            phon_text = content[:end]
        else:
            phon_text = content.split()[0] if content.split() else ""
        if phon_text.strip():
            phonetic = "/" + _clean_phonetic(phon_text).strip("/") + "/"
    elif z[:1] in ("'", "ˈ", "`", "‘"):
        # 开斜杠丢失（如 'ha:dli）→ 保留重音符，补成 /.../
        content = z
        end = content.find("/")
        phon_text = content[:end] if end >= 0 else (content.split()[0] if content.split() else "")
        if phon_text.strip():
            phonetic = "/" + _clean_phonetic(phon_text) + "/"

    # --- 括号内容 ---
    extended = zone + rest[pos_start:pos_start + 3]  # 词性提示可能在 zone 之外
    i = 0
    while i < len(zone):
        if zone[i] not in "(（":
            i += 1
            continue
        depth = 1
        j = i + 1
        while j < len(zone) and depth:
            if zone[j] in "(（":
                depth += 1
            elif zone[j] in ")）]":
                depth -= 1
            j += 1
        content = zone[i + 1:j - 1]
        after = extended[j:j + 2]  # 括号后紧跟的词性提示
        if "复" in content:
            part = content.split("复")[-1]
            form_m = re.match(r"[^/,，)]+", part)
            if form_m and form_m.group(0).strip():
                word_forms.append(
                    {"type": "plural", "form": form_m.group(0).strip(), "source": "document"}
                )
        elif re.match(r"^v[ .&]", after or " ") and not re.search(r"的|美", content):
            groups = [
                re.sub(r"/[^/]*/?", "", g).strip()
                for g in re.split(r"[,，]", content)
            ]
            groups = [g for g in groups if g]
            type_map = {
                1: ["past"],
                2: ["past", "past_participle"],
                3: ["third_person", "past", "past_participle"],
            }
            for t, g in zip(type_map.get(len(groups), []), groups):
                word_forms.append({"type": t, "form": g, "source": "document"})
        # 其他括号（=变体、说明等）忽略
        i = j

    # --- meanings ---
    meaning_text = rest[pos_start:] if pos else rest[search_from:]
    units += _UNIT_RE.findall(meaning_text)
    meanings = _parse_meanings(meaning_text, pos[1] if pos else None)

    return {
        "word": word,
        "phonetic": phonetic,
        "exam_level": exam_level,
        "meanings": meanings,
        "word_forms": word_forms,
        "units": units,
    }


def _parse_meanings(text: str, first_pos: str | None) -> list[dict]:
    """按词性链切段。text 以第一条词性链开头（或无词性）。"""
    out = []
    if first_pos is None:
        meaning = _UNIT_RE.sub("", text).strip()
        if meaning:
            out.append({"pos": "", "meaning": meaning})
        return out
    # 找出所有深度0的词性链位置
    spans = []
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "(（[":
            depth += 1
        elif ch in ")）]":
            depth = max(0, depth - 1)
        elif depth == 0:
            m = _POS_CHAIN_RE.match(text, i)
            if m:
                spans.append((m.start(), m.end(), m.group(1)))
                i = m.end()
                continue
        i += 1
    if not spans or spans[0][0] != 0:
        # 词性链之后才是 meaning_text 的情形已保证 spans[0][0]==0
        pass
    for k, (s, e, chain) in enumerate(spans):
        seg_end = spans[k + 1][0] if k + 1 < len(spans) else len(text)
        meaning = _UNIT_RE.sub("", text[e:seg_end]).strip(" ；;，,")
        if meaning:
            out.append({"pos": chain.strip().replace(" ", "").rstrip("&").rstrip(":："), "meaning": meaning})
    return out
