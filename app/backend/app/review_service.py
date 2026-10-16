"""学习服务：今日任务组卷 + 作答提交（SM-2 入库 + 错词记录 + 错题本联动）。"""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import sm2, vocab_store
from app.models import UserWordState, WordErrorRecord, WordLearningRecord


class WordNotFound(Exception):
    pass


def deck_today(db: Session, user_id: int, new_limit: int = 10) -> dict:
    """到期复习 + 新词。due 按到期时间排序；new 按 exam_level 降序随机。"""
    now = datetime.now()
    due_rows = (
        db.execute(
            select(UserWordState).where(
                UserWordState.user_id == user_id,
                UserWordState.next_review_date.isnot(None),
                UserWordState.next_review_date <= now,
            ).order_by(UserWordState.next_review_date).limit(100)
        ).scalars().all()
    )
    due = [{"word_id": s.word_id, "word": vocab_store.get_by_id(s.word_id)["word"]}
           for s in due_rows if vocab_store.get_by_id(s.word_id)]

    learned_ids = set(db.execute(
        select(UserWordState.word_id).where(UserWordState.user_id == user_id)
    ).scalars())

    new = []
    for wj in vocab_store.iter_words_ordered():
        if wj["id"] not in learned_ids:
            new.append({"word_id": wj["id"], "word": wj["word"]})
            if len(new) >= new_limit:
                break

    return {"due": due, "new": new}


def submit_review(
    db: Session,
    user_id: int,
    word_id: str,
    mode: str,
    quality: int,
    wrong_answer: str | None = None,
    response_ms: int | None = None,
    mistake_client=None,
) -> dict:
    """提交一次作答：SM-2 更新状态、写流水、错词写错误记录并联动错题本。

    mistake_client: 可注入的联动函数 f(word_rec, wrong_answer, mode, user) -> None。
    """
    if mode not in ("card", "choice", "spell"):
        raise ValueError(f"invalid mode: {mode}")
    if quality not in (1, 2, 3, 5):  # 我们的三模式映射白名单
        raise ValueError(f"invalid quality: {quality}")
    rec = vocab_store.get_by_id(word_id)
    if rec is None:
        raise WordNotFound(word_id)

    state = db.execute(
        select(UserWordState).where(
            UserWordState.user_id == user_id, UserWordState.word_id == word_id)
    ).scalar_one_or_none()
    if state is None:
        state = UserWordState(user_id=user_id, word_id=word_id,
                              ef=2.5, interval_days=0, rep_count=0, lapses=0)
        db.add(state)

    out = sm2.calculate(quality, state.ef, state.interval_days, state.rep_count)
    state.ef = out["new_ef"]
    state.interval_days = out["new_interval"]
    state.rep_count = out["new_rep_count"]
    state.next_review_date = datetime.combine(out["next_review_date"], time(8, 0))
    state.last_mode = mode
    if quality < 3:
        state.lapses = (state.lapses or 0) + 1

    db.add(WordLearningRecord(
        user_id=user_id, word_id=word_id, mode=mode, quality=quality,
        correct=quality >= 3, response_ms=response_ms))
    if quality < 3:
        db.add(WordErrorRecord(
            user_id=user_id, word_id=word_id, mode=mode,
            wrong_answer=wrong_answer or ""))

    db.commit()

    if quality < 3 and mistake_client is not None:
        try:
            mistake_client(rec, wrong_answer or "", mode)
        except Exception:  # 联动失败不影响作答主流程
            import logging
            logging.getLogger("wordapp").warning("错题本联动失败", exc_info=True)

    return {
        "word_id": word_id,
        "new_ef": out["new_ef"],
        "new_interval": out["new_interval"],
        "new_rep_count": out["new_rep_count"],
        "next_review_date": out["next_review_date"].isoformat(),
    }


def stats(db: Session, user_id: int) -> dict:
    """学习统计：已学/掌握/连续天数/今日待复习/薄弱词。"""
    total = vocab_store.word_count()
    states = db.execute(select(UserWordState).where(UserWordState.user_id == user_id)).scalars().all()
    learned = len(states)
    mastered = sum(1 for s in states if s.rep_count >= 1 and s.interval_days >= 7)
    now = datetime.now()
    due_today = sum(1 for s in states if s.next_review_date and s.next_review_date <= now)
    # 连续天数：按学习流水的日期，从今天/昨天往前数
    days = set(db.execute(
        select(func.date(WordLearningRecord.created_at)).where(
            WordLearningRecord.user_id == user_id)
    ).scalars())
    streak = 0
    d = datetime.now().date()
    from datetime import timedelta as _td
    if d.isoformat() not in days:
        d -= _td(days=1)
    while d.isoformat() in days:
        streak += 1
        d -= _td(days=1)
    weak = sorted(
        (s for s in states if s.lapses > 0), key=lambda s: -s.lapses)[:5]
    weak_words = []
    for s in weak:
        rec = vocab_store.get_by_id(s.word_id)
        if rec:
            weak_words.append({"word_id": s.word_id, "word": rec["word"], "lapses": s.lapses})
    return {
        "total_words": total,
        "learned": learned,
        "mastered": mastered,
        "streak_days": streak,
        "due_today": due_today,
        "weak_words": weak_words,
    }
