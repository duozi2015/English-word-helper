"""T6: 今日任务与作答提交（SQLite 替身用户库）。"""
from datetime import datetime, timedelta

import pytest

from app import review_service
from app.models import UserWordState, WordErrorRecord, WordLearningRecord
from app.migrations import run_migrations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

requires_vocab = pytest.mark.skipif(
    not __import__("pathlib").Path(__file__).resolve().parent.parent.parent.parent
    .joinpath("output/vocabulary.db").exists(),
    reason="词库未生成")


@pytest.fixture
def db():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(text("INSERT INTO users (id) VALUES (1)"))
    run_migrations(eng)
    return sessionmaker(bind=eng)()


from sqlalchemy import text  # noqa: E402


class TestDeckToday:
    @requires_vocab
    def test_new_words_only_for_fresh_user(self, db):
        deck = review_service.deck_today(db, user_id=1, new_limit=5)
        assert len(deck["new"]) == 5
        assert deck["due"] == []
        item = deck["new"][0]
        assert set(item) == {"word_id", "word", "phonetic"}

    @requires_vocab
    def test_due_words_appear(self, db):
        # 制造一条到期复习
        review_service.submit_review(db, 1, "V00520", "card", 5)
        # 首答后 next_review = 明天 → 今天无 due
        deck = review_service.deck_today(db, 1)
        assert all(d["word_id"] != "V00520" for d in deck["due"])
        # 把日期改到昨天
        st = db.query(UserWordState).filter_by(user_id=1, word_id="V00520").one()
        st.next_review_date = datetime.now() - timedelta(days=1)
        db.commit()
        deck = review_service.deck_today(db, 1)
        assert any(d["word_id"] == "V00520" for d in deck["due"])

    @requires_vocab
    def test_learned_word_not_in_new(self, db):
        review_service.submit_review(db, 1, "V00520", "card", 5)
        deck = review_service.deck_today(db, 1)
        assert all(d["word_id"] != "V00520" for d in deck["new"])


class TestSubmitReview:
    @requires_vocab
    def test_first_review_creates_state_and_record(self, db):
        out = review_service.submit_review(db, 1, "V00520", "card", 5)
        assert out["new_interval"] == 1 and out["new_rep_count"] == 1  # 首答 1 天台阶
        st = db.query(UserWordState).filter_by(user_id=1, word_id="V00520").one()
        assert st.ef == 2.5 and st.last_mode == "card"  # 阶梯算法不再改 EF
        assert db.query(WordLearningRecord).filter_by(user_id=1).count() == 1

    @requires_vocab
    def test_wrong_answer_writes_error_record(self, db):
        review_service.submit_review(db, 1, "V00520", "spell", 1, wrong_answer="recieve")
        err = db.query(WordErrorRecord).filter_by(user_id=1).one()
        assert err.wrong_answer == "recieve" and err.mode == "spell"
        st = db.query(UserWordState).filter_by(word_id="V00520").one()
        assert st.lapses == 1

    @requires_vocab
    def test_correct_answer_no_error_record(self, db):
        review_service.submit_review(db, 1, "V00520", "choice", 5)
        assert db.query(WordErrorRecord).count() == 0

    @requires_vocab
    def test_invalid_word_404(self, db):
        with pytest.raises(review_service.WordNotFound):
            review_service.submit_review(db, 1, "V99999", "card", 5)

    @requires_vocab
    def test_invalid_quality_raises(self, db):
        with pytest.raises(ValueError):
            review_service.submit_review(db, 1, "V00520", "card", 4)

    @requires_vocab
    def test_upsert_repeats(self, db):
        review_service.submit_review(db, 1, "V00520", "card", 5)
        out2 = review_service.submit_review(db, 1, "V00520", "choice", 5)
        assert out2["new_interval"] == 2  # 阶梯表：1→2
        assert db.query(UserWordState).filter_by(user_id=1).count() == 1
