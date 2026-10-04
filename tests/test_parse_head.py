"""T4: parse_entry.parse_head 测试 — 词头行解析（真实样本）。"""
from wordhelper.parse_entry import parse_head


class TestWordAndPhonetic:
    def test_basic(self):
        r = parse_head("?265.*chance /t?a:ns/ n.机会")
        assert r["word"] == "chance"
        assert r["phonetic"] == "/t?a:ns/"
        assert r["exam_level"] == 1

    def test_no_star(self):
        r = parse_head("1271.railway/'rerlwei/ n.铁路，铁道")
        assert r["word"] == "railway"
        assert r["exam_level"] == 0

    def test_three_stars(self):
        r = parse_head("?266.***change /tfernd?/v.改变，变化；更换；兑换(零钱)")
        assert r["word"] == "change"
        assert r["exam_level"] == 3

    def test_space_after_seq(self):
        r = parse_head("? 2.*able/erbl/ adj.能够的；有能力的")
        assert r["word"] == "able"

    def test_sense_number_stripped(self):
        r = parse_head("? 1.*ability①/'brl?ti/(复abilities) n.能力，才能，本领")
        assert r["word"] == "ability"

    def test_unclosed_phonetic(self):
        """OCR 丢失右斜杠。"""
        r = parse_head("?1135. passport/'pa:sp?:t n.护照")
        assert r["word"] == "passport"
        assert r["phonetic"] == "/'pa:sp?:t/"  # 补齐右斜杠

    def test_phonetic_missing_open_slash(self):
        """OCR 丢失左斜杠（重音符开头）。"""
        r = parse_head("?720.***hardly 'ha:dli adv.几乎不；几乎没有")
        assert r["word"] == "hardly"
        assert r["phonetic"] == "/'ha:dli/"

    def test_phonetic_open_slash_is_quote(self):
        """OCR 把左斜杠识别为引号。"""
        r = parse_head('?744.*hero"hr?r?u/(复heroes) n.英雄，勇士；男主角')
        assert r["word"] == "hero"
        assert r["phonetic"] == "/hr?r?u/"
        assert r["word_forms"] == [{"type": "plural", "form": "heroes", "source": "document"}]

    def test_phonetic_before_paren(self):
        r = parse_head("10.cast/ka:st(cast/ka:st/, cast)v.投(钓线);抛(钓钩)")
        assert r["word"] == "cast"
        assert r["phonetic"] == "/ka:st/"  # 丢失的右斜杠被补齐

    def test_proper_noun_keeps_case(self):
        r = parse_head("1127. Paris /p?ris/ n.(法国首都)巴黎")
        assert r["word"] == "Paris"

    def test_abbreviation(self):
        r = parse_head("58.Rd.(=road) abbr:路；道路(U5)")
        assert r["word"] == "Rd."
        assert r["meanings"] == [{"pos": "abbr", "meaning": "路；道路"}]

    def test_phrase_entry_no_phonetic(self):
        r = parse_head("72. break down损坏；衰弱下来")
        assert r["word"] == "break down"
        assert r["phonetic"] == ""
        assert r["meanings"] == [{"pos": "", "meaning": "损坏；衰弱下来"}]

    def test_multiword_with_star(self):
        r = parse_head("53.**be late for⋯⋯迟到")
        assert r["word"] == "be late for"
        assert r["exam_level"] == 2
        assert r["meanings"] == [{"pos": "", "meaning": "⋯⋯迟到"}]


class TestMeanings:
    def test_simple_n(self):
        r = parse_head("?1271.*rain /ren/n.雨，雨水")
        assert r["meanings"] == [{"pos": "n.", "meaning": "雨，雨水"}]

    def test_n_and_v(self):
        r = parse_head("?272.*chat /t??t/ n.&v.聊天，闲谈")
        assert r["meanings"] == [{"pos": "n.&v.", "meaning": "聊天，闲谈"}]

    def test_two_pos_groups(self):
        r = parse_head("?266.***change /tfernd?/v.改变，变化；更换；兑换(零钱)")
        assert r["meanings"][0] == {"pos": "v.", "meaning": "改变，变化；更换；兑换(零钱)"}

    def test_int_pos(self):
        r = parse_head("229.bye /bai/ int.再见")
        assert r["meanings"] == [{"pos": "int.", "meaning": "再见"}]

    def test_meaning_with_paren_chinese(self):
        r = parse_head("?564.fan/f?n/n.(电影、运动等的)迷；热心的爱好者(支持者);扇子")
        assert r["meanings"] == [{"pos": "n.", "meaning": "(电影、运动等的)迷；热心的爱好者(支持者);扇子"}]

    def test_adj(self):
        r = parse_head("17.awake /a'werk/(awoke /'w?uk/,awoken/a'w?uk?n/)v.(使)醒来；唤起；激发起")
        assert r["meanings"][0]["pos"] == "v."

    def test_variant_spelling_paren_ignored(self):
        r = parse_head("112.humour/hju:m?(r)/(<美〉humor) n.幽默；幽默感")
        assert r["word"] == "humour"
        assert r["meanings"] == [{"pos": "n.", "meaning": "幽默；幽默感"}]


class TestWordFormsFromDocument:
    def test_plural(self):
        r = parse_head("? 1.*ability①/'brl?ti/(复abilities) n.能力，才能，本领")
        assert r["word_forms"] == [{"type": "plural", "form": "abilities", "source": "document"}]

    def test_plural_with_phonetic(self):
        r = parse_head("602.*fisherman/'fi?om?n/(复fishermen/fif?m?n/) n.渔夫，渔民；钓鱼的人")
        forms = r["word_forms"]
        assert forms == [{"type": "plural", "form": "fishermen", "source": "document"}]

    def test_verb_two_forms(self):
        r = parse_head("17.awake /a'werk/(awoke /'w?uk/,awoken/a'w?uk?n/)v.(使)醒来；唤起；激发起")
        types = {f["type"] for f in r["word_forms"]}
        assert types == {"past", "past_participle"}
        forms = {f["type"]: f["form"] for f in r["word_forms"]}
        assert forms["past"] == "awoke"
        assert forms["past_participle"] == "awoken"

    def test_verb_with_or(self):
        r = parse_head("?603.fit/fit/(fit/fit/,fit或fitted/fitud/,fitted)v.(形状和尺寸)适合，合身")
        forms = {f["type"]: f["form"] for f in r["word_forms"]}
        assert forms["past"] == "fit或fitted"
        assert forms["past_participle"] == "fitted"

    def test_explanation_paren_ignored(self):
        r = parse_head("1519.stuck/stak/(stick的过去式和过去分词)adj.被卡住的，被困住的")
        assert r["word_forms"] == []

    def test_cast_document_forms(self):
        r = parse_head("10.cast/ka:st(cast/ka:st/, cast)v.投(钓线);抛(钓钩)")
        forms = {f["type"]: f["form"] for f in r["word_forms"]}
        assert forms["past"] == "cast"
        assert forms["past_participle"] == "cast"


class TestTextbookMarker:
    def test_unit_in_head(self):
        r = parse_head("4.blog/bl?g/(=weblog/weblbg/) n.博客；网志(U3)")
        assert r["units"] == ["3"]

    def test_no_unit(self):
        r = parse_head("?265.*chance /t?a:ns/ n.机会")
        assert r["units"] == []
