"""SM-2 间隔重复算法（与错题本 backend/app/services/sm2.py 同公式，便于合并维护）。

quality: 0-5（我们的映射：card 5/3/1、choice 5/2、spell 5/3/1）
"""
from __future__ import annotations

from datetime import date, timedelta


def calculate(quality: int, ef: float, interval: int, rep_count: int) -> dict:
    """按 SM-2 计算新参数。返回 new_ef/new_interval/new_rep_count/next_review_date。"""
    if not (0 <= quality <= 5):
        raise ValueError(f"quality must be between 0 and 5, got {quality}")

    ef = max(1.3, ef)
    if interval < 0:
        interval = 0
    if rep_count < 0:
        rep_count = 0

    if quality < 3:
        # 答错：重置
        new_ef = _next_ef(ef, quality)
        new_interval = 1
        new_rep_count = 0
    else:
        new_ef = _next_ef(ef, quality)
        if rep_count == 0:
            new_interval = 1
        elif rep_count == 1:
            new_interval = 6
        else:
            new_interval = round(interval * new_ef)
        new_rep_count = rep_count + 1

    new_interval = max(1, new_interval)
    return {
        "new_ef": round(new_ef, 2),
        "new_interval": new_interval,
        "new_rep_count": new_rep_count,
        "next_review_date": date.today() + timedelta(days=new_interval),
    }


def _next_ef(ef: float, quality: int) -> float:
    """EF' = EF + (0.1 - (5-q)*(0.08 + (5-q)*0.02))，下限 1.3。"""
    new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(1.3, new_ef)


# ---- 三模式的 quality 映射（design2.md §4）----

QUALITY_BY_CARD = {"know": 5, "fuzzy": 3, "unknown": 1}
QUALITY_BY_CHOICE = {True: 5, False: 2}
QUALITY_BY_SPELL = {"perfect": 5, "hinted": 3, "wrong": 1}
