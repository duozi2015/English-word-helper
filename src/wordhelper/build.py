"""T8: 组装 Vocabulary 记录 + id 分配。

输入 segment 产物（entries），输出 Schema 纯净记录（JSONL 用）
与 meta（seq/section/page/original_phonetic，SQLite 附表用）。
音标为技术债务：phonetic 置 ""，OCR 原串留底 meta。
"""
from __future__ import annotations

import json
from pathlib import Path

from wordhelper.parse_entry import parse_entry_text
from wordhelper.wordforms import complete_word_forms


def build_records(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    partials = []
    for e in entries:
        rec = parse_entry_text(e["text"], e["section"])
        pos = rec["meanings"][0]["pos"] if rec["meanings"] else ""
        rec["word_forms"] = complete_word_forms(rec["word"], pos, rec["word_forms"])
        # 音标技术债务（design.md §5）
        original_phonetic = rec["phonetic"]
        rec["phonetic"] = ""
        partials.append({
            "rec": rec,
            "seq": e["seq"],
            "section": e["section"],
            "page": e["start_page"],
            "original_phonetic": original_phonetic,
            "warnings": list(e.get("warnings", [])),
        })

    # id 按 word 字典序稳定分配（同词时按区段顺序）
    partials.sort(key=lambda p: (p["rec"]["word"], _SECTION_ORDER.get(p["section"], 9), p["seq"]))
    records, meta = [], []
    for i, p in enumerate(partials, 1):
        vid = f"V{i:05d}"
        p["rec"]["id"] = vid
        records.append(p["rec"])
        meta.append({
            "id": vid,
            "word": p["rec"]["word"],
            "seq": p["seq"],
            "section": p["section"],
            "page": p["page"],
            "original_phonetic": p["original_phonetic"],
            "warnings": p["warnings"],
        })
    return records, meta


_SECTION_ORDER = {"words": 0, "phrases": 1, "level3": 2, "jxjy": 3, "textbook": 4}


def save_outputs(records: list[dict], meta: list[dict], out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "vocabulary.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (out / "vocab_meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
