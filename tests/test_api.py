import os
from fastapi.testclient import TestClient

os.environ.setdefault("OMNI_DB_PATH", "./test_omni_hud.sqlite3")
from backend.main import app
from backend.analysis import ground_evidence, _domain

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


def test_rejects_blank_page_text():
    response = client.post("/api/analyze", json={
        "url": "https://example.com/article", "title": "Empty",
        "text": " " * 50, "comments": []
    })
    assert response.status_code == 422


def test_analysis_and_history_without_provider(monkeypatch, tmp_path):
    from backend import main

    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.sqlite3")
    main.init_db()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = client.post("/api/analyze", json={
        "url": "https://www.example.com/article", "title": "Example",
        "text": "This is a sufficiently long sample article body used to test the local fallback without an API key.",
        "comments": []
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["result"]["provider"] == "local-fallback"
    assert data["result"]["raw_truth"]["plain_language_summary"]
    assert data["result"]["domain"] == "example.com"

    history = client.get("/api/history?domain=example.com")
    assert history.status_code == 200
    assert any(item["id"] == data["analysis_id"] for item in history.json()["items"])

    detail = client.get(f"/api/history/{data['analysis_id']}")
    assert detail.status_code == 200
    assert detail.json()["result"]["url"] == "https://www.example.com/article"

    missing = client.get("/api/history/999999")
    assert missing.status_code == 404


def test_ground_evidence_removes_unverifiable_quotes():
    data = {
        "overall_confidence": "high",
        "caveats": [],
        "incentives": {"evidence": [
            {"excerpt": "exact phrase", "observation": "observed", "interpretation": "inference", "confidence": "high"},
            {"excerpt": "invented phrase", "observation": "observed", "interpretation": "inference", "confidence": "high"}
        ]},
        "spin": {"evidence": []},
        "psychology": {"evidence": []}
    }
    result = ground_evidence(data, "This contains an exact   phrase in the article.", [])
    assert len(result["incentives"]["evidence"]) == 1
    assert result["incentives"]["evidence"][0]["excerpt"] == "exact phrase"
    assert result["overall_confidence"] == "low"
    assert any("removed" in caveat for caveat in result["caveats"])


def test_domain_normalization():
    assert _domain("https://www.Example.com/article") == "example.com"



def test_backup_exports_complete_history(monkeypatch, tmp_path):
    from backend import main

    monkeypatch.setattr(main, "DB_PATH", tmp_path / "backup.sqlite3")
    main.init_db()
    saved_result = {"summary": "Saved analysis", "provider": "local-fallback"}
    with main.connection() as db:
        db.execute(
            "INSERT INTO analyses(url,domain,title,analyzed_at,provider,result_json) VALUES(?,?,?,?,?,?)",
            ("https://example.com/story", "example.com", "Story", "2026-10-24T12:00:00+00:00",
             "local-fallback", __import__("json").dumps(saved_result)),
        )

    response = client.get("/api/backup")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    backup = response.json()
    assert backup["backup_format"] == "omni-hud-history"
    assert backup["backup_version"] == 1
    assert backup["record_count"] == 1
    assert backup["records"][0]["result"] == saved_result
    assert "result_json" not in backup["records"][0]
