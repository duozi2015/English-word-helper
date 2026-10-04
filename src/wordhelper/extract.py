"""T1: PDF → Raw Pages 提取。

每页输出 {page: 1-based页码, text: 整页文本, lines: [{y, text}]}，
lines 按阅读顺序（y 坐标）排列，坐标供后续排序/分栏判断使用。
"""
from __future__ import annotations

import json
from pathlib import Path


def extract_pages(pdf_path: str | Path) -> list[dict]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    pages = []
    try:
        for pno in range(doc.page_count):
            pages.append(_extract_page(doc[pno], pno + 1))
    finally:
        doc.close()
    return pages


def _extract_page(page, page_number: int) -> dict:
    raw = page.get_text("dict")
    lines = []
    for block in raw["blocks"]:
        if block.get("type") != 0:  # 只处理文本块
            continue
        for line in block["lines"]:
            spans = [span["text"] for span in line["spans"] if span["text"].strip()]
            if not spans:
                continue
            lines.append({"y": round(line["bbox"][1], 1), "text": "".join(spans).strip()})
    lines.sort(key=lambda l: l["y"])
    return {
        "page": page_number,
        "text": page.get_text(),
        "lines": lines,
    }


def save_pages(pages: list[dict], out_path: str | Path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    import sys

    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "output/raw/pages.json"
    pages = extract_pages(pdf)
    save_pages(pages, out)
    print(f"{len(pages)} pages -> {out}")
