"""T5: parse_entry.parse_entry_text 测试 — 标记段与例句配对（真实词条）。"""
from wordhelper.parse_entry import parse_entry_text

ADVICE = """?25.*advice/?dvars/ n.忠告，劝告，建议，意见
G7上U4The manager thought the old lady was right, but he didn't take her advice.
经理认为这位老太太是正确的，但他没有接受她的忠告。
词形拓展
advise v.劝告，忠告，建议
常用词组
take one's advice听从某人劝告
近义 opinion; suggestion
名师点拨 advice是常考单词，相当于an opinion/a suggestion,所以学生一定要掌握
其固定搭配：
ask for one's advice=ask sb. for advice征求某人的意见
take/follow one's advice听从某人的劝告"""

ACT = """?12.*act /?kt/ v.表演，扮演(角色);行动
G6下U6
n.行动
The actor who acted in the TV series last night became famous in his thirties.
昨晚电视剧中的这位演员，在他30多岁时就成名了。
His selfless act of kindness touched everyone's heart.他无私的善举触动了每个人的心。
词形拓展
acting n.表演
action n.行动；行为过程
常用词组
act out 表演
谚语 Think well before you act.三思而后行。"""

FIT = """?603.fit/fit/(fit/fit/,fit或fitted/fitud/,fitted)v.(形状和尺寸)适合，合身；与⋯⋯相配
G8下U4
adj.健康的；合适的
Do you have any ready-made clothes that will fit me?你们这儿有适合我穿的成衣吗?
You look very fit.你看上去很健康。
词形拓展
unfit adj.不适合的
常用词组
keep fit保持健康"""


class TestAdviceEntry:
    def setup_method(self):
        self.r = parse_entry_text(ADVICE, section="words")

    def test_word(self):
        assert self.r["word"] == "advice"

    def test_example_from_g_line(self):
        ex = self.r["examples"]
        assert len(ex) == 1
        assert ex[0]["en"].startswith("The manager thought")
        assert ex[0]["zh"] == "经理认为这位老太太是正确的，但他没有接受她的忠告。"
        assert ex[0]["type"] == "general"

    def test_textbook_from_g_line(self):
        assert self.r["textbook"] == [{"grade": "七", "semester": "上", "unit": "4"}]

    def test_related_words_from_cixing(self):
        rw = [w for w in self.r["related_words"] if w["relation"] == "词形拓展"]
        assert len(rw) == 1
        assert rw[0] == {"word": "advise", "pos": "v.", "meaning": "劝告，忠告，建议",
                         "relation": "词形拓展"}

    def test_phrases(self):
        assert self.r["phrases"] == [{"text": "take one's advice", "meaning": "听从某人劝告"}]

    def test_jinyi(self):
        rw = self.r["related_words"]
        words = [w["word"] for w in rw if w["relation"] == "相关词"]
        assert set(words) == {"opinion", "suggestion"}

    def test_teaching_note(self):
        tn = self.r["teaching_notes"]
        assert len(tn) == 1
        assert tn[0]["type"] in ("usage", "exam_tip")
        assert "advice是常考单词" in tn[0]["content"]


class TestActEntry:
    def setup_method(self):
        self.r = parse_entry_text(ACT, section="words")

    def test_meanings_two_pos(self):
        ms = self.r["meanings"]
        assert ms == [{"pos": "v.", "meaning": "表演，扮演(角色);行动"},
                      {"pos": "n.", "meaning": "行动"}]

    def test_two_examples(self):
        ex = self.r["examples"]
        assert len(ex) == 2
        assert ex[0]["en"].startswith("The actor who acted")
        assert ex[1]["en"].startswith("His selfless act")
        assert ex[1]["zh"] == "他无私的善举触动了每个人的心。"

    def test_multiple_cixing_items(self):
        rw = [w for w in self.r["related_words"] if w["relation"] == "词形拓展"]
        assert {w["word"] for w in rw} == {"acting", "action"}

    def test_proverb(self):
        assert self.r["proverbs"] == [
            {"text": "Think well before you act.", "meaning": "三思而后行。"}
        ]


class TestFitEntry:
    def setup_method(self):
        self.r = parse_entry_text(FIT, section="words")

    def test_meanings_from_two_blocks(self):
        ms = self.r["meanings"]
        assert ms[0]["pos"] == "v."
        assert ms[1] == {"pos": "adj.", "meaning": "健康的；合适的"}

    def test_document_word_forms(self):
        forms = {f["type"]: f["form"] for f in self.r["word_forms"]}
        assert forms["past"] == "fit或fitted"

    def test_phrase_keep_fit(self):
        assert self.r["phrases"] == [{"text": "keep fit", "meaning": "保持健康"}]

    def test_example_mixed_line(self):
        ex = self.r["examples"]
        assert ex[0]["en"] == "Do you have any ready-made clothes that will fit me?"
        assert ex[0]["zh"] == "你们这儿有适合我穿的成衣吗?"
        assert ex[1] == {"en": "You look very fit.", "zh": "你看上去很健康。", "type": "general"}


class TestTags:
    def test_words_tag(self):
        r = parse_entry_text(ADVICE, section="words")
        assert r["tags"] == ["考纲"]

    def test_level3_tag(self):
        r = parse_entry_text(ACT, section="level3")
        assert r["tags"] == ["三级词汇"]


class TestEmptyFields:
    def test_all_fields_present(self):
        r = parse_entry_text(ACT, section="words")
        for key in ("collocations", "usage_notes"):
            assert r[key] == []
        assert r["id"] == ""


class TestOcrEdgeCases:
    def test_touch_screen_fake_paren(self):
        """OCR 音标内的假括号不破坏释义解析。"""
        text = "74.touch screen/'tat( skri:n/n.(计算机)触摸屏(U2)\nThis computer has a touch screen.这台电脑有触摸屏。"
        r = parse_entry_text(text, section="textbook")
        assert r["word"] == "touch screen"
        assert r["phonetic"] == "/'tat( skri:n/"
        assert r["meanings"] == [{"pos": "n.", "meaning": "(计算机)触摸屏"}]
        assert r["textbook"] == [{"grade": "", "semester": "", "unit": "2"}]

    def test_phonetic_prefix_continuation(self):
        """transport 型：续行以音标开头。"""
        text = ("1634. transport/tr?n'sp?:t/ v.运输，运送；输送\n"
                "/'tr?nsp?:t/ n.运输；输送；运送；交通车辆\n"
                "A helicopter was used to transport the wounded. 一架直升飞机被用来运送伤员。")
        r = parse_entry_text(text, section="words")
        assert r["meanings"][0] == {"pos": "v.", "meaning": "运输，运送；输送"}
        assert r["meanings"][1] == {"pos": "n.", "meaning": "运输；输送；运送；交通车辆"}
        assert len(r["examples"]) == 1
        assert r["usage_notes"] == []
