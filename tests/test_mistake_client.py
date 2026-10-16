

class TestDeckReviewEndpoints:
    def test_full_flow(self, capture, monkeypatch):
        import pathlib
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.main import app
        from app.database import get_db

        if not pathlib.Path("../../output/vocabulary.db").exists():
            pytest.skip("词库未生成")
        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        with eng.begin() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            conn.execute(text("INSERT INTO users (id) VALUES (1)"))
        run_migrations(eng)
        TestSession = sessionmaker(bind=eng)
        app.dependency_overrides[get_db] = lambda: TestSession()
        app.dependency_overrides[get_current_user] = lambda: {
            "id": 1, "username": "dou", "display_name": "小豆", "role": "student"}
        try:
            c = TestClient(app)
            deck = c.get("/words/api/deck/today", headers={"Authorization": "Bearer t"}).json()
            wid = deck["new"][0]["word_id"]
            out = c.post("/words/api/review", json={"word_id": wid, "mode": "spell",
                                                    "quality": 1, "wrong_answer": "abc"},
                         headers={"Authorization": "Bearer t"})
            assert out.status_code == 200
            assert out.json()["new_interval"] == 1
            assert len(capture) == 1  # 联动已触发
        finally:
            app.dependency_overrides.clear()

    def test_review_unknown_word_404(self, capture, monkeypatch):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.main import app
        from app.database import get_db

        eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        run_migrations(eng)
        app.dependency_overrides[get_db] = lambda: sessionmaker(bind=eng)()
        app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "dou", "display_name": "", "role": "student"}
        try:
            r = TestClient(app).post("/words/api/review", json={"word_id": "V99999", "mode": "card", "quality": 5},
                                     headers={"Authorization": "Bearer t"})
            assert r.status_code == 404
        finally:
            app.dependency_overrides.clear()
