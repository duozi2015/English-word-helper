"""T5: SM-2 状态机测试（含与错题本实现对拍的手算基准）。"""
from datetime import date, timedelta

import pytest

from app.sm2 import QUALITY_BY_CARD, QUALITY_BY_CHOICE, QUALITY_BY_SPELL, calculate


class TestFormula:
    def test_invalid_quality_raises(self):
        for q in (-1, 6):
            with pytest.raises(ValueError):
                calculate(q, 2.5, 0, 0)

    def test_first_correct_interval_1(self):
        r = calculate(5, 2.5, 0, 0)
        assert (r["new_ef"], r["new_interval"], r["new_rep_count"]) == (2.6, 1, 1)

    def test_second_correct_interval_6(self):
        r = calculate(5, 2.6, 1, 1)
        assert (r["new_ef"], r["new_interval"], r["new_rep_count"]) == (2.7, 6, 2)

    def test_third_multiplies_by_ef(self):
        # 6 * 2.8 = 16.8 → 17
        r = calculate(5, 2.8, 6, 2)
        assert r["new_interval"] == 17

    def test_wrong_resets(self):
        # q=1: EF 2.5 + (0.1 - 4*(0.08+4*0.02)) = 2.5 + (0.1 - 0.64) = 1.96
        r = calculate(1, 2.5, 15, 5)
        assert (r["new_ef"], r["new_interval"], r["new_rep_count"]) == (1.96, 1, 0)

    def test_ef_floor_13(self):
        r = calculate(0, 1.3, 0, 0)
        assert r["new_ef"] == 1.3

    def test_quality3_ef_formula(self):
        # q=3: 0.1 - 2*(0.08+2*0.02) = -0.14 → 2.36
        assert calculate(3, 2.5, 0, 0)["new_ef"] == 2.36

    def test_next_review_date(self):
        r = calculate(5, 2.5, 0, 0)
        assert r["next_review_date"] == date.today() + timedelta(days=1)

    def test_interval_never_below_1(self):
        assert calculate(5, 2.5, 0, 0)["new_interval"] >= 1


class TestSequence:
    def test_remembering_word_streak(self):
        """连续认识：1 → 6 → 17 → 49 天（手算：6*2.8=16.8→17, 17*2.9=49.3→49）。"""
        ef, interval, rep = 2.5, 0, 0
        intervals = []
        for _ in range(4):
            r = calculate(5, ef, interval, rep)
            ef, interval, rep = r["new_ef"], r["new_interval"], r["new_rep_count"]
            intervals.append(interval)
        assert intervals == [1, 6, 17, 49]


class TestMappings:
    def test_card_mapping(self):
        assert QUALITY_BY_CARD == {"know": 5, "fuzzy": 3, "unknown": 1}

    def test_choice_mapping(self):
        assert QUALITY_BY_CHOICE == {True: 5, False: 2}

    def test_spell_mapping(self):
        assert QUALITY_BY_SPELL == {"perfect": 5, "hinted": 3, "wrong": 1}
