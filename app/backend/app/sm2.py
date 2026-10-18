"""单词记忆曲线：百词斩式阶梯表（design2.md 决策 2026-10-18）。

固定台阶 1→2→4→7→15→30→60 天：
- 答对（quality>=5）升一级
- 模糊（quality==3）原地踏步
- 答错（quality<=2）回到 1 天
与错题本的 SM-2 引擎分道扬镳：单词节奏短平快、台阶可预期。
calculate() 签名与旧版保持一致（review_service 无需改动）。
"""
from __future__ import annotations

from datetime import date, timedelta

LADDER = [1, 2, 4, 7, 15, 30, 60]


def calculate(quality: int, ef: float, interval: int, rep_count: int) -> dict:
    """按阶梯表计算新参数。

    interval 传当前间隔天数（历史 SM-2 数据自动映射到最近台阶）。
    返回 new_ef/new_interval/new_rep_count/next_review_date（ef 保留字段，阶梯算法不用）。
    """
    if not (0 <= quality <= 5):
        raise ValueError(f"quality must be between 0 and 5, got {quality}")

    level = _level_from_interval(interval)

    if quality >= 5:
        # 首次作答落在 1 天台阶；此后逐级上爬
        new_level = 0 if (rep_count == 0 and interval == 0) else min(level + 1, len(LADDER) - 1)
    elif quality >= 3:
        new_level = level  # 模糊：原地踏步
    else:
        new_level = 0  # 答错：回到起点

    new_interval = LADDER[new_level]
    return {
        "new_ef": ef,
        "new_interval": new_interval,
        "new_rep_count": new_level + 1,
        "next_review_date": date.today() + timedelta(days=new_interval),
    }


def _level_from_interval(interval: int) -> int:
    """当前间隔天数 → 阶梯级别（历史 SM-2 数据向下取最近台阶）。"""
    if interval <= 0:
        return 0
    level = 0
    for i, days in enumerate(LADDER):
        if days <= interval:
            level = i
    return level


# ---- 三模式的 quality 映射（design2.md §4）----

QUALITY_BY_CARD = {"know": 5, "fuzzy": 3, "unknown": 1}
QUALITY_BY_CHOICE = {True: 5, False: 2}
QUALITY_BY_SPELL = {"perfect": 5, "hinted": 3, "wrong": 1}
