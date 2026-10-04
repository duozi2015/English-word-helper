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


# ==================== T5: 完整词条解析 ====================

_SECTION_TAGS = {
    "words": ["考纲"],
    "phrases": ["考纲"],
    "level3": ["三级词汇"],
    "jxjy": ["学科教学基本要求"],
    "textbook": ["教材"],
}
_MARKERS = ("词形拓展", "词组拓展", "常用词组", "近义", "反义", "谚语", "名师点拨", "名师点拔", "用法")
_G_RE = re.compile(r"^G(\d)\s*([上下])\s*U?(\d{1,2})")
_GRADE_CN = {"6": "六", "7": "七", "8": "八"}
_MIXED_RE = re.compile(r"^([" + "A-Za-z0-9 .,'()&!?;:%-]*?[.?!]?)(" + "[" + _CJK + "].*)$")
_EN_START_RE = re.compile(r"^[A-Za-z\"'(]")


def _line_kind(line: str) -> str:
    """'en' / 'zh' / 'mixed'。"""
    if not _EN_START_RE.match(line):
        return "zh"
    if re.search("[" + _CJK + "]", line):
        return "mixed"
    return "en"


def _split_mixed(line: str) -> tuple[str, str]:
    m = re.match(r"^(.*?)([" + _CJK + "].*)$", line)
    return m.group(1).strip(), m.group(2).strip()


class _Pairer:
    """英文行/中文行配对器。"""

    def __init__(self):
        self.en: list[str] = []
        self.zh: list[str] = []

    def add(self, kind: str, text: str, out: list, en_join: str = " ", zh_join: str = ""):
        if kind == "en":
            if self.zh:
                self.flush(out, en_join, zh_join)
            self.en.append(text)
        elif kind == "zh":
            if self.en:
                self.zh.append(text)
            else:  # 孤立中文行交还调用方
                return text
        return None

    def flush(self, out: list, en_join: str = " ", zh_join: str = ""):
        if self.en:
            out.append({"en": en_join.join(self.en).strip(),
                        "zh": zh_join.join(self.zh).strip(), "type": "general"})
        self.en, self.zh = [], []


def _marker_item(item: str, relation: str) -> dict | None:
    """词形拓展/近义条目：word + 可选 pos/meaning。"""
    m = re.match(r"[A-Za-z][A-Za-z0-9'-]*", item)
    if not m:
        return None
    word = m.group(0)
    rest = item[m.end():].strip()
    pos, meaning = "", ""
    pm = _POS_CHAIN_RE.match(rest)
    if pm and rest[pm.end():].strip():
        pos = pm.group(1).strip().replace(" ", "").rstrip("&").rstrip(":：")
        meaning = rest[pm.end():].strip(" ；;，,")
    elif not pm:
        meaning = "" if re.search("[" + _CJK + "]", rest) else ""
    return {"word": word, "pos": pos, "meaning": meaning, "relation": relation}


def _classify_teaching_type(content: str) -> str:
    if "辨析" in content:
        return "comparison"
    if "错" in content:
        return "common_error"
    if any(k in content for k in ("考点", "中考", "考试", "常考")):
        return "exam_tip"
    if any(k in content for k in ("语法", "时态", "句型")):
        return "grammar"
    return "usage"


def parse_entry_text(text: str, section: str) -> dict:
    lines = text.split("\n")
    base = parse_head(lines[0])
    units = list(base["units"])  # (grade, semester, unit) 尚未归一

    examples, proverbs, related, phrases_out = [], [], [], []
    usage_blocks, teaching = [], []
    head_extra = []  # 词义续行
    cur_marker = None
    marker_buf: dict[str, list[str]] = {}
    pairer = _Pairer()

    def flush_pair(target: list):
        pairer.flush(target)

    def add_unit(u):
        units.append(u)

    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            continue
        marker = next((m for m in _MARKERS if line.startswith(m)), None)
        if marker:
            flush_pair(examples)
            cur_marker = "名师点拨" if marker == "名师点拔" else marker
            marker_buf.setdefault(cur_marker, [])
            inline = line[len(marker):].strip()
            if inline:
                marker_buf[cur_marker].append(inline)
            continue
        gm = _G_RE.match(line)
        if gm:
            flush_pair(examples)
            cur_marker = None
            add_unit((gm.group(1), gm.group(2), gm.group(3)))
            rest = line[gm.end():].strip()
            if rest:
                kind = _line_kind(rest)
                if kind == "mixed":
                    en, zh = _split_mixed(rest)
                    orphan = pairer.add("en", en, examples)
                    pairer.add("zh", zh, examples)
                else:
                    pairer.add(kind, rest, examples)
            continue
        if cur_marker is None:
            # 词义续行：以词性链开头的中文行
            pm = _POS_CHAIN_RE.match(line)
            if pm and re.search("[" + _CJK + "]", line[pm.end():]):
                flush_pair(examples)
                head_extra.append(line)
                continue
            kind = _line_kind(line)
            if kind == "mixed":
                en, zh = _split_mixed(line)
                orphan = pairer.add("en", en, examples)
                if orphan:
                    usage_blocks.append(orphan)
                orphan2 = pairer.add("zh", zh, examples)
                if orphan2:
                    usage_blocks.append(orphan2)
            elif kind == "zh" and not pairer.en:
                usage_blocks.append(line)
            else:
                orphan = pairer.add(kind, line, examples)
                if orphan:
                    usage_blocks.append(orphan)
        else:
            marker_buf[cur_marker].append(line)
    flush_pair(examples)

    # --- 标记段产出 ---
    for mk, blines in marker_buf.items():
        if mk in ("近义", "反义"):
            for item in blines:
                for w in re.split(r"[;；,、]", item):
                    w = w.strip()
                    if w:
                        r = _marker_item(w, "相关词")
                        if r:
                            related.append(r)
        elif mk == "词形拓展":
            for item in blines:
                r = _marker_item(item, "词形拓展")
                if r:
                    related.append(r)
        elif mk in ("常用词组", "词组拓展"):
            for item in blines:
                en, zh = _split_mixed(item) if _line_kind(item) == "mixed" else (item, "")
                if en.strip():
                    phrases_out.append({"text": en.strip(), "meaning": zh})
        elif mk == "谚语":
            p = _Pairer()
            sink: list = []
            for item in blines:
                kind = _line_kind(item)
                if kind == "mixed":
                    en, zh = _split_mixed(item)
                    orphan = p.add("en", en, sink)
                    p.add("zh", zh, sink)
                else:
                    p.add(kind, item, sink)
            p.flush(sink)
            for e in sink:
                proverbs.append({"text": e["en"], "meaning": e["zh"]})
        elif mk == "名师点拨":
            content = "\n".join(blines).strip()
            if content:
                teaching.append({"type": _classify_teaching_type(content),
                                 "title": "", "content": content})
        elif mk == "用法":
            usage_blocks.extend(blines)

    # --- 词义续行解析 ---
    meanings = list(base["meanings"])
    for hl in head_extra:
        pm = _POS_CHAIN_RE.match(hl)
        if pm:
            meanings += _parse_meanings(hl[pm.start():], pm.group(1))

    textbook = []
    for u in units:
        if isinstance(u, tuple) and len(u) == 3 and u[2]:
            textbook.append({"grade": _GRADE_CN.get(u[0], u[0]),
                             "semester": u[1], "unit": u[2]})
        elif isinstance(u, str):  # 仅 (U5) 形式，年级/学期取决于所在章节
            textbook.append({"grade": "", "semester": "", "unit": u})

    return {
        "id": "",
        "word": base["word"],
        "phonetic": base["phonetic"],
        "meanings": meanings,
        "word_forms": base["word_forms"],
        "related_words": related,
        "phrases": phrases_out,
        "collocations": [],
        "proverbs": proverbs,
        "examples": examples,
        "usage_notes": usage_blocks,
        "teaching_notes": teaching,
        "tags": list(_SECTION_TAGS.get(section, [])),
        "exam_level": base["exam_level"],
        "textbook": textbook,
    }
