"""T7: 规则化词形补全（受控，source=ai）。

优先级：PDF 明确出现（word_forms 标记/词头括号内，source=document）优先；
缺失形式按规则引擎补全（source=ai）。无法可靠生成的形式不生成。
"""
from __future__ import annotations

# 不规则动词表：(第三人称单数, 过去式, 过去分词, 现在分词)
# 现在分词为 None 表示按规则生成
_IRREGULAR_VERBS: dict[str, tuple[str, str, str]] = {
    "be": ("is", "was/were", "been"),
    "am": ("", "was", "been"),
    "is": ("", "was", "been"),
    "are": ("", "were", "been"),
    "have": ("has", "had", "had"),
    "do": ("does", "did", "done"),
    "go": ("goes", "went", "gone"),
    "come": ("comes", "came", "come"),
    "become": ("becomes", "became", "become"),
    "run": ("runs", "ran", "run"),
    "eat": ("eats", "ate", "eaten"),
    "drink": ("drinks", "drank", "drunk"),
    "swim": ("swims", "swam", "swum"),
    "begin": ("begins", "began", "begun"),
    "sing": ("sings", "sang", "sung"),
    "ring": ("rings", "rang", "rung"),
    "sink": ("sinks", "sank", "sunk"),
    "give": ("gives", "gave", "given"),
    "take": ("takes", "took", "taken"),
    "shake": ("shakes", "shook", "shaken"),
    "see": ("sees", "saw", "seen"),
    "write": ("writes", "wrote", "written"),
    "drive": ("drives", "drove", "driven"),
    "ride": ("rides", "rode", "ridden"),
    "rise": ("rises", "rose", "risen"),
    "speak": ("speaks", "spoke", "spoken"),
    "break": ("breaks", "broke", "broken"),
    "steal": ("steals", "stole", "stolen"),
    "choose": ("chooses", "chose", "chosen"),
    "freeze": ("freezes", "froze", "frozen"),
    "wake": ("wakes", "woke", "woken"),
    "wear": ("wears", "wore", "worn"),
    "tear": ("tears", "tore", "torn"),
    "fly": ("flies", "flew", "flown"),
    "grow": ("grows", "grew", "grown"),
    "know": ("knows", "knew", "known"),
    "throw": ("throws", "threw", "thrown"),
    "draw": ("draws", "drew", "drawn"),
    "blow": ("blows", "blew", "blown"),
    "show": ("shows", "showed", "shown"),
    "buy": ("buys", "bought", "bought"),
    "bring": ("brings", "brought", "brought"),
    "think": ("thinks", "thought", "thought"),
    "catch": ("catches", "caught", "caught"),
    "teach": ("teaches", "taught", "taught"),
    "fight": ("fights", "fought", "fought"),
    "seek": ("seeks", "sought", "sought"),
    "sell": ("sells", "sold", "sold"),
    "tell": ("tells", "told", "told"),
    "stand": ("stands", "stood", "stood"),
    "understand": ("understands", "understood", "understood"),
    "sit": ("sits", "sat", "sat"),
    "get": ("gets", "got", "got/gotten"),
    "forget": ("forgets", "forgot", "forgotten"),
    "feel": ("feels", "felt", "felt"),
    "keep": ("keeps", "kept", "kept"),
    "sleep": ("sleeps", "slept", "slept"),
    "sweep": ("sweeps", "swept", "swept"),
    "leave": ("leaves", "left", "left"),
    "mean": ("means", "meant", "meant"),
    "lend": ("lends", "lent", "lent"),
    "send": ("sends", "sent", "sent"),
    "spend": ("spends", "spent", "spent"),
    "build": ("builds", "built", "built"),
    "find": ("finds", "found", "found"),
    "make": ("makes", "made", "made"),
    "say": ("says", "said", "said"),
    "pay": ("pays", "paid", "paid"),
    "lay": ("lays", "laid", "laid"),
    "hear": ("hears", "heard", "heard"),
    "win": ("wins", "won", "won"),
    "shine": ("shines", "shone", "shone"),
    "hold": ("holds", "held", "held"),
    "meet": ("meets", "met", "met"),
    "feed": ("feeds", "fed", "fed"),
    "lead": ("leads", "led", "led"),
    "lose": ("loses", "lost", "lost"),
    "hit": ("hits", "hit", "hit"),
    "cut": ("cuts", "cut", "cut"),
    "put": ("puts", "put", "put"),
    "let": ("lets", "let", "let"),
    "set": ("sets", "set", "set"),
    "shut": ("shuts", "shut", "shut"),
    "hurt": ("hurts", "hurt", "hurt"),
    "cost": ("costs", "cost", "cost"),
    "read": ("reads", "read", "read"),
    "learn": ("learns", "learnt/learned", "learnt/learned"),
    "fall": ("falls", "fell", "fallen"),
    "deal": ("deals", "dealt", "dealt"),
    "dig": ("digs", "dug", "dug"),
    "hang": ("hangs", "hung/hanged", "hung/hanged"),
    "stick": ("sticks", "stuck", "stuck"),
    "strike": ("strikes", "struck", "struck"),
    "spell": ("spells", "spelt/spelled", "spelt/spelled"),
    "hide": ("hides", "hid", "hidden"),
    "bite": ("bites", "bit", "bitten"),
    "beat": ("beats", "beat", "beaten"),
    "mistake": ("mistakes", "mistook", "mistaken"),
    "spread": ("spreads", "spread", "spread"),
}

# 不规则名词复数
_IRREGULAR_PLURALS = {
    "child": "children",
    "foot": "feet",
    "tooth": "teeth",
    "goose": "geese",
    "man": "men",
    "woman": "women",
    "mouse": "mice",
    "person": "people",
    "leaf": "leaves",
    "life": "lives",
    "knife": "knives",
    "wife": "wives",
    "shelf": "shelves",
    "wolf": "wolves",
    "thief": "thieves",
    "half": "halves",
    "loaf": "loaves",
    "sheep": "sheep",
    "deer": "deer",
    "fish": "fish",
    "Chinese": "Chinese",
}

# 单复数同形 / 复数专形（不生成复数）
_PLURALIA_TANTUM = {
    "maths", "physics", "politics", "police", "cattle", "trousers",
    "pants", "shorts", "jeans", "scissors", "glasses", "sunglasses",
    "chopsticks", "thanks", "congratulations", " Olympics", "people",
    "today", "tonight", "tomorrow", "yesterday",
}

# 不可数/无复数名词（受控原则：拿不准不生成）
_UNCOUNTABLE = {
    "health", "information", "advice", "news", "weather", "homework",
    "housework", "furniture", "music", "progress", "fun", "bread",
    "water", "milk", "rice", "tea", "juice", "meat", "chicken", "food",
    "money", "traffic", "chalk", "paper", "wood", "glass", "work",
    "time", "people", "clothing", "luggage", "baggage", "equipment",
    "knowledge", "harm", "help", "luck", "peace", "practice", "research",
    "room", "space", "stuff", "sugar", "salt", "snow", "rain", "wind",
    "sunshine", "smoke", "noise", "love", "hate", "anger", "joy",
}

# 不规则比较级/最高级
_IRREGULAR_COMP = {
    "good": ("better", "best"),
    "well": ("better", "best"),
    "bad": ("worse", "worst"),
    "badly": ("worse", "worst"),
    "ill": ("worse", "worst"),
    "many": ("more", "most"),
    "much": ("more", "most"),
    "little": ("less", "least"),
    "far": ("farther/further", "farthest/furthest"),
    "old": ("older/elder", "oldest/eldest"),
    "late": ("later/latter", "latest/last"),
}

# 无比较级的常用副词/形容词（受控原则：不生成）
_NO_COMP = {
    "quite", "rather", "almost", "nearly", "very", "too", "also",
    "already", "always", "never", "often", "seldom", "usually",
    "here", "there", "now", "then", "again", "ever", "once",
}

# 长形容词后缀（more/most 型，不生成 -er/-est）
_LONG_ADJ_SUFFIXES = (
    "ful", "ous", "ing", "ed", "al", "ive", "able", "ible", "ant",
    "ent", "ess", "ish", "like", "less", "ward",

)

_VOWELS = set("aeiou")


def _third_person(word: str) -> str:
    if word.endswith(("ch", "sh", "x", "s", "z", "o")):
        return word + "es"
    if word.endswith("y") and word[-2:-1] and word[-2] not in _VOWELS:
        return word[:-1] + "ies"
    return word + "s"


def _cvc_doubles(word: str) -> bool:
    """单音节 CVC 结尾且非 l/w/x/y → 双写尾辅音。保守判断。"""
    if len(word) < 3 or len(word) > 7:
        return False
    a, b, c = word[-3], word[-2], word[-1]
    return (
        a not in _VOWELS and b in _VOWELS and c not in _VOWELS
        and c not in "lwxy" and word[-4:-3] not in _VOWELS or False
    ) or (len(word) == 3 and a not in _VOWELS and b in _VOWELS and c not in _VOWELS and c not in "lwxy")


def _past_stem(word: str) -> str:
    if word.endswith("e"):
        return word + "d"
    if word.endswith("y") and word[-2:-1] and word[-2] not in _VOWELS:
        return word[:-1] + "i"
    return word + "e" if False else word


def _verb_forms(word: str) -> list[dict]:
    out = []
    if word in _IRREGULAR_VERBS:
        third, past, pp = _IRREGULAR_VERBS[word]
        if third:
            out.append(("third_person", third))
        out += [("past", past), ("past_participle", pp)]
        pp_ing = None
    else:
        out.append(("third_person", _third_person(word)))
        if word.endswith("y") and word[-2:-1] and word[-2] not in _VOWELS:
            past = word[:-1] + "ied"
        elif word.endswith("e"):
            past = word + "d"
        elif _cvc_doubles(word):
            past = word + word[-1] + "ed"
        else:
            past = word + "ed"
        out.append(("past", past))
    # 过去分词（规则动词同过去式）
    has_pp = any(t == "past_participle" for t, _ in out)
    if not has_pp:
        out.append(("past_participle", out[-1][1] if word not in _IRREGULAR_VERBS else None))
    # 现在分词
    if word.endswith("ie"):
        ing = word[:-2] + "ying"
    elif word.endswith("e") and word not in ("be",):
        ing = word[:-1] + "ing"
    elif _cvc_doubles(word):
        ing = word + word[-1] + "ing"
    else:
        ing = word + "ing"
    out.append(("present_participle", ing))
    # 清理 None
    return [(t, f) for t, f in out if f]


def _noun_forms(word: str) -> list[dict]:
    if word in _UNCOUNTABLE or word in _PLURALIA_TANTUM:
        return []
    if word in _IRREGULAR_PLURALS:
        return [("plural", _IRREGULAR_PLURALS[word])]
    if word.endswith(("s", "x", "ch", "sh", "z")):
        return [("plural", word + "es")]
    if word.endswith("y") and word[-2:-1] and word[-2] not in _VOWELS:
        return [("plural", word[:-1] + "ies")]
    if word.endswith("f") and word not in ("roof", "chief", "proof", "serf"):
        return [("plural", word[:-1] + "ves")]
    if word.endswith("fe"):
        return [("plural", word[:-2] + "ves")]
    return [("plural", word + "s")]


def _adj_forms(word: str) -> list[dict]:
    if word in _IRREGULAR_COMP or word in _NO_COMP:
        comp, sup = _IRREGULAR_COMP.get(word, (None, None))
        if comp:
            return [("comparative", comp), ("superlative", sup)]
        return []
    # 以 -er 结尾（either/other/another 等虚指词）不生成比较级
    if word.endswith("er"):
        return []
    # 长形容词/多音节不生成
    if word.endswith(_LONG_ADJ_SUFFIXES) or len(word) >= 7:
        return []
    if word.endswith("y") and word[-2:-1] and word[-2] not in _VOWELS:
        return [("comparative", word[:-1] + "ier"), ("superlative", word[:-1] + "iest")]
    if word.endswith("e"):
        return [("comparative", word + "r"), ("superlative", word + "st")]
    if _cvc_doubles(word):
        return [("comparative", word + word[-1] + "er"), ("superlative", word + word[-1] + "est")]
    return [("comparative", word + "er"), ("superlative", word + "est")]


def complete_word_forms(word: str, pos: str, document_forms: list[dict]) -> list[dict]:
    """PDF 已有形式优先，缺失的按规则补全（source=ai）。"""
    if not pos or " " in word:
        return []
    # 专有名词（首字母大写且不在不规则表中）不生成，避免 Pacifics 之类
    if word[0].isupper() and word not in _IRREGULAR_PLURALS and word not in _IRREGULAR_VERBS:
        return []
    doc_types = {f["type"] for f in document_forms}
    generated: list[tuple[str, str]] = []
    pos_clean = pos.rstrip(".")
    parts = [p.strip().strip(".") for p in pos_clean.split("&") if p.strip()]
    for part in parts:
        if part == "n":
            generated += _noun_forms(word)
        elif part == "v":
            generated += _verb_forms(word)
        elif part in ("adj", "adv"):
            generated += _adj_forms(word)
    out = list(document_forms)
    seen_types = doc_types
    for t, form in generated:
        if form and t not in seen_types:
            out.append({"type": t, "form": form, "source": "ai"})
    return out
