import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analysis import analyze
from .schemas import AnalyzeRequest, AnalyzeResponse

DB_PATH = Path(os.getenv("OMNI_DB_PATH", "./omni_hud.sqlite3")).resolve()
MAX_TEXT = int(os.getenv("OMNI_MAX_TEXT_CHARS", "18000"))
app = FastAPI(title="OMNI-HUD API", version="0.1.0",
              description="Evidence-led, four-lens webpage analysis with local history.")

# This API is intended to bind to loopback. Permit extension origins for local use.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*",
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL, domain TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
            analyzed_at TEXT NOT NULL, provider TEXT NOT NULL, result_json TEXT NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_analyses_domain ON analyses(domain)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_analyses_time ON analyses(analyzed_at)")

init_db()

@app.get("/health")
def health():
    return {"status": "ok", "service": "omni-hud", "database": str(DB_PATH),
            "provider_configured": bool(os.getenv("GROQ_API_KEY", "").strip())}

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_page(request: AnalyzeRequest):
    parsed = urlparse(request.url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=422, detail="url must be an absolute http(s) URL")
    text = request.text[:MAX_TEXT]
    try:
        result = await analyze(request.url, request.title, text, request.comments)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"Analysis response was invalid: {type(exc).__name__}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analysis provider failed ({type(exc).__name__}). Check provider configuration and logs.") from exc
    with connection() as db:
        cursor = db.execute(
            "INSERT INTO analyses(url,domain,title,analyzed_at,provider,result_json) VALUES(?,?,?,?,?,?)",
            (result["url"], result["domain"], result.get("title", ""),
             result["analyzed_at"], result["provider"], json.dumps(result, ensure_ascii=False)))
        analysis_id = cursor.lastrowid
    return {"analysis_id": analysis_id, "result": result}

@app.get("/api/history")
def history(domain: str | None = None, q: str | None = None,
            limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    sql = "SELECT id,url,domain,title,analyzed_at,provider FROM analyses"
    clauses, params = [], []
    if domain:
        clauses.append("domain = ?"); params.append(domain.lower().removeprefix("www."))
    if q:
        clauses.append("(title LIKE ? OR url LIKE ? OR result_json LIKE ?)")
        needle = f"%{q[:200]}%"; params.extend([needle, needle, needle])
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"; params.extend([limit, offset])
    with connection() as db:
        rows = db.execute(sql, params).fetchall()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}

@app.get("/api/history/{analysis_id}")
def history_detail(analysis_id: int):
    with connection() as db:
        row = db.execute("SELECT id,result_json FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"analysis_id": row["id"], "result": json.loads(row["result_json"])}

@app.get("/api/domains")
def domain_summaries(limit: int = Query(default=50, ge=1, le=200)):
    with connection() as db:
        rows = db.execute("""SELECT domain, COUNT(*) AS analyses,
            MAX(analyzed_at) AS last_analyzed FROM analyses
            GROUP BY domain ORDER BY analyses DESC, last_analyzed DESC LIMIT ?""", (limit,)).fetchall()
        scores = db.execute("SELECT domain,result_json FROM analyses ORDER BY id DESC").fetchall()
    grouped = {}
    for row in scores:
        grouped.setdefault(row["domain"], [])
        try:
            result = json.loads(row["result_json"])
            if result.get("provider") != "local-fallback":
                grouped[row["domain"]].append({
                    "incentive_rating": result.get("incentives", {}).get("rating"),
                    "spin_score": result.get("spin", {}).get("score")
                })
        except (ValueError, TypeError):
            continue
    output = []
    for row in rows:
        item = dict(row)
        observations = grouped.get(row["domain"], [])
        incentive_values = [x["incentive_rating"] for x in observations if isinstance(x["incentive_rating"], int)]
        spin_values = [x["spin_score"] for x in observations if isinstance(x["spin_score"], int)]
        item["scored_analyses"] = len(observations)
        item["mean_incentive_signal"] = round(sum(incentive_values) / len(incentive_values), 1) if incentive_values else None
        item["mean_framing_signal"] = round(sum(spin_values) / len(spin_values), 1) if spin_values else None
        output.append(item)
    return {"domains": output}

@app.get("/")
def root():
    return {"name": "Project OMNI-HUD", "docs": "/docs", "health": "/health"}
