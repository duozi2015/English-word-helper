"""T5: 阶梯表记忆算法测试（百词斩式，替代原 SM-2）。"""
from datetime import date, timedelta

import pytest

from app.sm2 import LADDER, QUALITY_BY_CARD, QUALITY_BY_CHOICE, QUALITY_BY_SPELL, calculate


class TestLadder:
    def test_invalid_quality_raises(self):
        for q in (-1, 6):
            with pytest.raises(ValueError):
                calculate(q, 2.5, 0, 0)

    def test_first_correct_1_day(self):
        r = calculate(5, 2.5, 0, 0)
        assert r["new_interval"] == 1 and r["new_rep_count"] == 1

    def test_consecutive_correct_climb(self):
        """连续答对：1→2→4→7→15→30→60→60（封顶）。"""
        intervals = []
        interval, rep = 0, 0
        for _ in range(8):
            r = calculate(5, 2.5, interval, rep)
            interval, rep = r["new_interval"], r["new_rep_count"]
            intervals.append(interval)
        assert intervals == [1, 2, 4, 7, 15, 30, 60, 60]

    def test_wrong_resets_to_1(self):
        r = calculate(1, 2.5, 30, 5)
        assert r["new_interval"] == 1

    def test_fuzzy_stays(self):
        """模糊原地踏步（间隔不变）。"""
        r = calculate(3, 2.5, 7, 3)
        assert r["new_interval"] == 7

    def test_choice_wrong_also_resets(self):
        r = calculate(2, 2.5, 15, 4)
        assert r["new_interval"] == 1

    def test_legacy_sm2_interval_maps_down(self):
        """历史 SM-2 数据（6/17/49 天）映射到最近台阶。"""
        assert calculate(5, 2.5, 6, 2)["new_interval"] == 7    # 6→level2(4)→升→7
        assert calculate(5, 2.5, 17, 2)["new_interval"] == 30  # 17→level3(15)→升→30
        assert calculate(5, 2.5, 49, 2)["new_interval"] == 60  # 49→level4(30)→升→60

    def test_fuzzy_on_legacy_interval_stays(self):
        assert calculate(3, 2.5, 17, 2)["new_interval"] == 15

    def test_next_review_date(self):
        r = calculate(5, 2.5, 0, 0)
        assert r["next_review_date"] == date.today() + timedelta(days=1)

    def test_ladder_definition(self):
        assert LADDER == [1, 2, 4, 7, 15, 30, 60]


class TestMappings:
    def test_card_mapping(self):
        assert QUALITY_BY_CARD == {"know": 5, "fuzzy": 3, "unknown": 1}

    def test_choice_mapping(self):
        assert QUALITY_BY_CHOICE == {True: 5, False: 2}

    def test_spell_mapping(self):
        assert QUALITY_BY_SPELL == {"perfect": 5, "hinted": 3, "wrong": 1}
