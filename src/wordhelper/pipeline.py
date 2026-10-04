"""T11: 全流程 CLI。

用法：
  python -m wordhelper.pipeline extract    # PDF → output/raw/pages.json
  python -m wordhelper.pipeline segment    # → output/raw/entries.json
  python -m wordhelper.pipeline build      # → output/vocabulary.jsonl + vocab_meta.json
  python -m wordhelper.pipeline validate   # → output/reports/*.md|json
  python -m wordhelper.pipeline export     # → output/vocabulary.db
  python -m wordhelper.pipeline all        # 以上全部
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PDF = ROOT / "pdf" / "2027年上海市初中英语考纲词汇用法手册 (1)(1).pdf"
SCHEMA = ROOT / "docs" / "上海初中英语AI学习产品_词汇JSONSchema_V1.2.json"
sys.path.insert(0, str(ROOT / "src"))

from wordhelper.extract import extract_pages, save_pages          # noqa: E402
from wordhelper.segment import split_book                         # noqa: E402
from wordhelper.build import build_records, save_outputs          # noqa: E402
from wordhelper.validate import (validate_schema,                 # noqa: E402
                                 consistency_report, phonetic_debt_list)
from wordhelper.export_db import export_db                        # noqa: E402


def step_extract() -> list[dict]:
    print("== extract: PDF → pages.json")
    pages = extract_pages(PDF)
    save_pages(pages, ROOT / "output/raw/pages.json")
    print(f"  {len(pages)} pages")
    return pages


def step_segment(pages: list[dict] | None = None) -> list[dict]:
    print("== segment: pages → entries.json")
    if pages is None:
        pages = json.load(open(ROOT / "output/raw/pages.json"))
    entries, sections = split_book(pages)
    with open(ROOT / "output/raw/entries.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    print(f"  {len(entries)} entries")
    return entries


def step_build(entries: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    print("== build: entries → vocabulary.jsonl")
    if entries is None:
        entries = json.load(open(ROOT / "output/raw/entries.json"))
    records, meta = build_records(entries)
    save_outputs(records, meta, ROOT / "output")
    print(f"  {len(records)} records")
    return records, meta


def step_validate(records=None, meta=None) -> dict:
    print("== validate: schema + consistency")
    if records is None:
        records = [json.loads(l) for l in open(ROOT / "output/vocabulary.jsonl")]
    if meta is None:
        meta = json.load(open(ROOT / "output/vocab_meta.json"))
    errors = validate_schema(records, str(SCHEMA))
    report = consistency_report(records, meta)
    report["schema_errors"] = errors

    out = ROOT / "output/reports"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "validate_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    with open(out / "phonetic_debt.json", "w", encoding="utf-8") as f:
        json.dump(phonetic_debt_list(meta), f, ensure_ascii=False, indent=1)
    _write_markdown_report(report, out)

    print(f"  schema错误: {len(errors)}, 例句配对率: {report['examples_pair_rate']}")
    return report


def _write_markdown_report(report: dict, out: Path) -> None:
    lines = ["# 词汇数据校验报告\n"]
    lines.append(f"- 总词条: {report['total']}")
    lines.append(f"- Schema 错误: {len(report['schema_errors'])}")
    lines.append(f"- 例句: {report['examples_total']} 句，配对率 {report['examples_pair_rate']}")
    lines.append(f"- 无释义词条: {len(report['no_meanings'])}")
    lines.append(f"- 区段分布: {report['by_section']}")
    lines.append(f"\n## 重复词 ({len(report['duplicate_words'])})\n")
    for d in report["duplicate_words"]:
        lines.append(f"- **{d['word']}** ×{d['count']}: {', '.join(d['ids'])}")
    lines.append(f"\n## 序号断点 ({len(report['seq_gaps'])})\n")
    for m in report["seq_gaps"]:
        lines.append(f"- {m['id']} {m['word']} ({m['section']}): {', '.join(m['warnings'])}")
    for e in report["schema_errors"][:50]:
        lines.append(f"- SCHEMA: {e}")
    (out / "validate_report.md").write_text("\n".join(lines), encoding="utf-8")


def step_export() -> None:
    print("== export: JSONL → SQLite")
    meta = json.load(open(ROOT / "output/vocab_meta.json"))
    export_db(str(ROOT / "output/vocabulary.jsonl"),
              str(ROOT / "output/vocabulary.db"), meta)
    print("  output/vocabulary.db")


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("extract", "all"):
        pages = step_extract()
    else:
        pages = None
    if cmd in ("segment", "all"):
        entries = step_segment(pages)
    else:
        entries = None
    if cmd in ("build", "all"):
        records, meta = step_build(entries)
    else:
        records = meta = None
    if cmd in ("validate", "all"):
        step_validate(records, meta)
    if cmd in ("export", "all"):
        step_export()
    if cmd not in ("extract", "segment", "build", "validate", "export", "all"):
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
