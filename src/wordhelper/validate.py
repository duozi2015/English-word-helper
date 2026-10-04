"""T9: Schema 校验 + 一致性质检。

Schema 校验用规范自带的 V1.2 JSON Schema；一致性质检覆盖：
序号连续性、重复词、例句配对率、音标债务清单。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def validate_schema(records: list[dict], schema_path: str) -> list[str]:
    import jsonschema

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for i, rec in enumerate(records):
        for e in validator.iter_errors(rec):
            errors.append(f"[{i}] {list(e.absolute_path)}: {e.message}")
    return errors


def consistency_report(records: list[dict], meta: list[dict]) -> dict:
    report: dict = {}
    report["total"] = len(records)

    # 重复词
    word_counts = Counter(r["word"] for r in records)
    report["duplicate_words"] = sorted(
        ({"word": w, "count": c, "ids": [r["id"] for r in records if r["word"] == w]}
         for w, c in word_counts.items() if c > 1),
        key=lambda d: -d["count"],
    )

    # 序号断点
    report["seq_gaps"] = [m for m in meta if m.get("warnings")]

    # 例句配对率：zh 为空的比例
    total_ex = sum(len(r["examples"]) for r in records)
    empty_zh = sum(1 for r in records for e in r["examples"] if not e["zh"])
    report["examples_total"] = total_ex
    report["examples_empty_zh"] = empty_zh
    report["examples_pair_rate"] = round(1 - empty_zh / total_ex, 4) if total_ex else 1.0

    # 无释义词条
    report["no_meanings"] = [r["id"] for r in records if not r["meanings"]]

    # 各区段词条数
    report["by_section"] = dict(Counter(m["section"] for m in meta))

    return report


def phonetic_debt_list(meta: list[dict]) -> list[dict]:
    """音标技术债务清单：所有非空 original_phonetic 的词条。"""
    return [
        {"id": m["id"], "word": m["word"], "original_phonetic": m["original_phonetic"],
         "section": m["section"], "page": m["page"]}
        for m in meta if m.get("original_phonetic")
    ]
