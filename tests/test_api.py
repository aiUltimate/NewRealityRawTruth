import os
from fastapi.testclient import TestClient

os.environ.setdefault("OMNI_DB_PATH", "./test_omni_hud.sqlite3")
from backend.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_rejects_non_http_url():
    response = client.post("/api/analyze", json={
        "url": "javascript:alert(1)", "title": "bad", "text": "x" * 50, "comments": []
    })
    assert response.status_code == 422

def test_analysis_and_history_without_provider(monkeypatch, tmp_path):
    from backend import main
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.sqlite3")
    main.init_db()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = client.post("/api/analyze", json={
        "url": "https://example.com/article", "title": "Example",
        "text": "This is a sufficiently long sample article body used to test the local fallback without an API key.",
        "comments": []
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["result"]["provider"] == "local-fallback"
    assert data["result"]["raw_truth"]["plain_language_summary"]
    history = client.get("/api/history")
    assert history.status_code == 200
    detail = client.get(f"/api/history/{data['analysis_id']}")
    assert detail.status_code == 200
