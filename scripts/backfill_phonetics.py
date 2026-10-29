"""音标技术债务回填：用 ipa-dict en_GB 词典查表修复 2531 条乱码音标。

债务背景：词汇源 PDF 为扫描版 + 隐形 OCR 文字层，音标 100% 乱码
（able→/erbl/），纯规则无法恢复。原 OCR 串保留于 meta.original_phonetic。

用法：
  python scripts/backfill_phonetics.py            # dry-run，只报匹配率
  python scripts/backfill_phonetics.py --apply    # 实际写库
  python scripts/backfill_phonetics.py --dict PATH
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phonetic_overrides import OVERRIDES as MANUAL_OVERRIDES  # noqa: E402

DB_PATH = REPO / "output" / "vocabulary.db"
DICT_PATH = REPO / "output" / "dicts" / "en_GB.txt"


def load_dict(path: Path) -> dict[str, list[str]]:
    """ipa-dict 格式：word<TAB>/ipa1, /ipa2（含 ;; 头部注释）。"""
    table: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if "\t" not in line:
            continue
        word, ipa = line.split("\t", 1)
        ipa = ipa.strip().strip("/").strip()
        if not ipa:
            continue
        variants = [v.strip().strip("/").strip() for v in ipa.split(",") if v.strip()]
        key = word.strip().lower()
        table.setdefault(key, []).extend(variants)
    return table


def lookup_candidates(word: str) -> list[str]:
    """同一单词的多种拼写形态，按优先级排列。"""
    w = word.strip().lower()
    cands = [w]
    if " " in w:
        cands.append(w.replace(" ", "-"))   # ipa-dict 复合词常用连字符
        cands.append(w.replace(" ", ""))
    if "-" in w:
        cands.append(w.replace("-", " "))
    return cands


# ── ipa-dict → 教材排版体系归一化 ──────────────────────────────────
# ipa-dict en_UK 风格：重音符在重读元音前（/wˈɔːtɐ/），且用 ɐ/ɹ；
# 教材风格：重音符在音节 onset 前（/ˈwɔːtə/），用 ə/r。

_VOWELS = set("aeiouɑæʌəɪʊɒɔːeɣiːuɜeɪaɪɔɪaʊəʊɪəeəʊəy")
_CONSONANTS = set("bdfɡklmnprstvzðθʃʒhtʃdʒjwɡɹɹ")
# 英语合法音节 onset（用于重音符定位），从长到短尝试
_ONSETS = [
    "skr", "spr", "str", "skw", "spl", "ʃr", "θr", "ðr",
    "pl", "pr", "bl", "br", "tr", "dr", "kl", "kr", "gl", "gr",
    "fl", "fr", "sl", "sm", "sn", "sp", "st", "sk", "sw", "tw",
    "dw", "kw", "gw", "tʃ", "dʒ", "mj", "nj", "bj", "dj", "gj",
    "fj", "vj", "θj", "sj",
]


def _fix_stress_mark(ipa: str, mark: str) -> str:
    """把重音符（ˈ/ˌ）移到所在音节的 onset 前（教材风格）。"""
    out = list(ipa)
    i = 0
    while i < len(out):
        if out[i] == mark:
            # 向前收集连续辅音串
            j = i - 1
            run = ""
            while j >= 0 and (out[j] in _CONSONANTS):
                run = out[j] + run
                j -= 1
            # run 的最长合法 onset 后缀（从最长开始尝试，命中即停）
            onset = ""
            for k in range(len(run)):
                suffix = run[k:]
                if suffix in _ONSETS or (len(suffix) == 1 and suffix in _CONSONANTS):
                    onset = suffix
                    break
            if run and onset:
                # 删除原位置：onset 部分留在 前，其余保持
                pre_len = len(run) - len(onset)
                # out[j+1 : i] 是 run；重排为 run[:pre_len] + mark + onset
                new_seg = run[:pre_len] + mark + onset
                out[j + 1 : i + 1] = list(new_seg)
                i = j + 1 + len(new_seg)
            else:
                i += 1
        else:
            i += 1
    return "".join(out)


def normalize_ipa(ipa: str) -> str:
    """ipa-dict 字形 → 教材字形。幂等：对教材风格串是恒等变换。"""
    if not ipa:
        return ipa
    s = ipa.replace("ɐ", "ə").replace("ɹ", "r")
    s = _fix_stress_mark(s, "ˈ")
    s = _fix_stress_mark(s, "ˌ")
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写库（默认 dry-run）")
    ap.add_argument("--dict", type=Path, default=DICT_PATH)
    args = ap.parse_args()

    if not args.dict.exists():
        print(f"词典不存在: {args.dict}")
        return 1

    table = load_dict(args.dict)
    print(f"词典词条数: {len(table)}")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT v.id, v.word, v.phonetic, m.original_phonetic "
        "FROM vocabulary v LEFT JOIN meta m ON m.id = v.id "
        "ORDER BY v.id"
    ).fetchall()

    matched = unmatched = already = 0
    unmatched_words: list[tuple[str, str]] = []
    updates: list[tuple[str, str]] = []

    for row in rows:
        word = row["word"]
        ipa = ""
        for cand in lookup_candidates(word):
            variants = table.get(cand)
            if variants:
                ipa = variants[0]
                break
        if not ipa and word.lower() in MANUAL_OVERRIDES:
            ipa = MANUAL_OVERRIDES[word.lower()]
        ipa = normalize_ipa(ipa)

        if row["phonetic"]:
            already += 1
            continue
        if ipa:
            matched += 1
            updates.append((ipa, row["id"]))
        else:
            unmatched += 1
            unmatched_words.append((row["id"], word, row["original_phonetic"] or ""))

    print(f"总词条: {len(rows)}｜已有音标: {already}｜本次可修复: {matched}｜未匹配: {unmatched}")
    rate = matched / (matched + unmatched) * 100 if (matched + unmatched) else 100
    print(f"匹配率: {rate:.1f}%（验收线 ≥90%）")

    if unmatched_words:
        print("\n未匹配词（前 40）:")
        for rid, w, orig in unmatched_words[:40]:
            print(f"  {rid}  {w}  原OCR串: {orig}")
        dump = REPO / "output" / "reports" / "phonetic_unmatched.json"
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_text(
            json.dumps(
                [{"id": rid, "word": w, "original_phonetic": orig}
                 for rid, w, orig in unmatched_words],
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
        print(f"完整未匹配清单: {dump}")

    if not args.apply:
        print("\n[dry-run] 未写库。加 --apply 执行写入。")
        return 0

    con.executemany("UPDATE vocabulary SET phonetic = ? WHERE id = ?", updates)
    con.commit()
    print(f"\n[apply] 已写入 {len(updates)} 条音标。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
