"""T7: wordforms.py 测试 — 规则化词形补全（source=ai）。"""
from wordhelper.wordforms import complete_word_forms


class TestVerbForms:
    def test_regular_verb(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("act", "v.", [])}
        assert forms["third_person"] == "acts"
        assert forms["past"] == "acted"
        assert forms["past_participle"] == "acted"
        assert forms["present_participle"] == "acting"
        assert all(f["source"] == "ai" for f in complete_word_forms("act", "v.", []))

    def test_irregular_verb_go(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("go", "v.", [])}
        assert forms["third_person"] == "goes"
        assert forms["past"] == "went"
        assert forms["past_participle"] == "gone"
        assert forms["present_participle"] == "going"

    def test_irregular_verb_catch(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("catch", "v.", [])}
        assert forms["past"] == "caught"
        assert forms["past_participle"] == "caught"

    def test_e_ending_verb(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("change", "v.", [])}
        assert forms["third_person"] == "changes"
        assert forms["past"] == "changed"
        assert forms["present_participle"] == "changing"

    def test_consonant_y_verb(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("study", "v.", [])}
        assert forms["third_person"] == "studies"
        assert forms["past"] == "studied"

    def test_document_forms_not_overwritten(self):
        """PDF 已有 past/pp 时只补缺失形式。"""
        doc = [{"type": "past", "form": "fit或fitted", "source": "document"},
               {"type": "past_participle", "form": "fitted", "source": "document"}]
        forms = {f["type"]: f["form"] for f in complete_word_forms("fit", "v.", doc)}
        assert forms["past"] == "fit或fitted"  # document 优先
        assert forms["past_participle"] == "fitted"
        assert forms["third_person"] == "fits"
        assert forms["present_participle"] == "fitting"


class TestNounForms:
    def test_regular_noun(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("accident", "n.", [])}
        assert forms == {"plural": "accidents"}

    def test_irregular_plural_child(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("child", "n.", [])}
        assert forms == {"plural": "children"}

    def test_f_to_ves(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("leaf", "n.", [])}
        assert forms == {"plural": "leaves"}

    def test_consonant_y_noun(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("factory", "n.", [])}
        assert forms == {"plural": "factories"}

    def test_uncountable_no_plural(self):
        """不可数名词不生成复数。"""
        assert complete_word_forms("health", "n.", []) == []
        assert complete_word_forms("information", "n.", []) == []

    def test_document_plural_kept(self):
        doc = [{"type": "plural", "form": "fishermen", "source": "document"}]
        forms = {f["type"]: f["form"] for f in complete_word_forms("fisherman", "n.", doc)}
        assert forms["plural"] == "fishermen"


class TestAdjForms:
    def test_regular_adj(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("hard", "adj.", [])}
        assert forms == {"comparative": "harder", "superlative": "hardest"}

    def test_e_ending_adj(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("large", "adj.", [])}
        assert forms == {"comparative": "larger", "superlative": "largest"}

    def test_cvcdoubling_adj(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("big", "adj.", [])}
        assert forms == {"comparative": "bigger", "superlative": "biggest"}

    def test_irregular_adj_good(self):
        forms = {f["type"]: f["form"] for f in complete_word_forms("good", "adj.", [])}
        assert forms == {"comparative": "better", "superlative": "best"}

    def test_long_adj_no_forms(self):
        """长形容词（more/most 型）不生成。"""
        assert complete_word_forms("beautiful", "adj.", []) == []
        assert complete_word_forms("famous", "adj.", []) == []


class TestPosHandling:
    def test_multi_pos(self):
        """n.&v. 生成两种词性的形式。"""
        forms = complete_word_forms("chat", "n.&v.", [])
        types = {f["type"] for f in forms}
        assert "plural" in types and "third_person" in types

    def test_no_pos_no_forms(self):
        assert complete_word_forms("break down", "", []) == []

    def test_prep_no_forms(self):
        assert complete_word_forms("above", "prep.", []) == []
