"""Read-only HTTP API for the supplier reliability scoring engine."""
import os
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from src.db import DEFAULT_DB_PATH

app = FastAPI(
    title="Supplier Reliability Scoring API",
    description="Read-only REST API for supplier scores, evidence confidence, and operational decisions.",
    version="1.0.0",
)


def get_database_path() -> Path:
    return Path(os.getenv("SUPPLIER_DB_PATH", str(DEFAULT_DB_PATH)))


def get_connection() -> sqlite3.Connection:
    db_path = get_database_path()
    if not db_path.is_file():
        raise HTTPException(
            status_code=503,
            detail="Scoring database is not initialized. Run 'python -m scripts.bootstrap_api_db' before starting the API.",
        )
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def latest_run_id(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        "SELECT run_id FROM score_runs ORDER BY run_timestamp DESC, rowid DESC LIMIT 1"
    ).fetchone()
    return row["run_id"] if row else None


@app.get("/", tags=["system"])
def root():
    return {"name": "Supplier Reliability Scoring API", "version": app.version,
            "docs": "/docs", "health": "/api/v1/health"}


@app.get("/api/v1/health", tags=["system"])
def health():
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
        run_id = latest_run_id(conn)
        if run_id is None:
            raise HTTPException(status_code=503, detail="Database exists but no scoring run is available.")
        return {"status": "ok", "database": "connected", "latest_run_id": run_id}
    finally:
        conn.close()


@app.get("/api/v1/summary", tags=["analytics"])
def summary():
    conn = get_connection()
    try:
        run_id = latest_run_id(conn)
        if run_id is None:
            raise HTTPException(status_code=503, detail="No scoring run is available.")
        rows = conn.execute(
            """SELECT d.classification, COUNT(*) AS supplier_count
               FROM supplier_scores s
               JOIN supplier_decisions d ON d.score_id = s.score_id
               WHERE s.run_id = ? GROUP BY d.classification ORDER BY d.classification""",
            (run_id,),
        ).fetchall()
        return {"run_id": run_id, "total_suppliers": sum(r["supplier_count"] for r in rows),
                "classification_counts": {r["classification"]: r["supplier_count"] for r in rows}}
    finally:
        conn.close()


@app.get("/api/v1/score-runs/latest", tags=["analytics"])
def latest_score_run():
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT run_id, run_timestamp, as_of_date, config_version,
                      config_hash, generator_version, random_seed
               FROM score_runs ORDER BY run_timestamp DESC, rowid DESC LIMIT 1"""
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="No scoring run found.")
        return dict(row)
    finally:
        conn.close()


@app.get("/api/v1/suppliers", tags=["suppliers"])
def list_suppliers(
    classification: Optional[str] = Query(default=None, description="Reliable, Watch, At Risk, or Insufficient Evidence"),
    search: Optional[str] = Query(default=None, min_length=1, max_length=100, description="Search supplier ID or name"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    allowed = {"Reliable", "Watch", "At Risk", "Insufficient Evidence"}
    if classification is not None and classification not in allowed:
        raise HTTPException(status_code=400, detail=f"classification must be one of: {', '.join(sorted(allowed))}")
    clauses = ["s.run_id = ?"]
    params: list = []
    conn = get_connection()
    try:
        run_id = latest_run_id(conn)
        if run_id is None:
            raise HTTPException(status_code=503, detail="No scoring run is available.")
        params.append(run_id)
        if classification:
            clauses.append("d.classification = ?")
            params.append(classification)
        if search:
            clauses.append("(p.supplier_id LIKE ? OR p.name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        where_sql = " AND ".join(clauses)
        total = conn.execute(
            f"""SELECT COUNT(*) FROM supplier_scores s
                JOIN supplier_decisions d ON d.score_id = s.score_id
                JOIN suppliers p ON p.supplier_id = s.supplier_id WHERE {where_sql}""",
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT p.supplier_id, p.name, p.category, p.country, p.status,
                       s.final_score, s.overall_confidence_tier,
                       d.classification, d.decision_reason
                FROM supplier_scores s
                JOIN supplier_decisions d ON d.score_id = s.score_id
                JOIN suppliers p ON p.supplier_id = s.supplier_id
                WHERE {where_sql}
                ORDER BY s.final_score DESC, p.supplier_id LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        ).fetchall()
        return {"run_id": run_id, "total": total, "limit": limit, "offset": offset,
                "items": [dict(row) for row in rows]}
    finally:
        conn.close()


@app.get("/api/v1/suppliers/{supplier_id}", tags=["suppliers"])
def get_supplier(supplier_id: str):
    conn = get_connection()
    try:
        run_id = latest_run_id(conn)
        if run_id is None:
            raise HTTPException(status_code=503, detail="No scoring run is available.")
        row = conn.execute(
            """SELECT p.supplier_id, p.name, p.category, p.country, p.status,
                      s.score_id, s.run_id, s.delivery_score, s.delivery_sample_count,
                      s.delivery_confidence, s.quality_score, s.quality_sample_count,
                      s.quality_confidence, s.cost_score, s.cost_sample_count,
                      s.cost_confidence, s.capacity_score, s.capacity_sample_count,
                      s.capacity_confidence, s.compliance_score, s.compliance_sample_count,
                      s.compliance_confidence, s.disruption_score, s.disruption_sample_count,
                      s.disruption_confidence, s.final_score, s.overall_confidence_tier,
                      d.classification, d.decision_reason, d.policy_version
               FROM suppliers p
               JOIN supplier_scores s ON s.supplier_id = p.supplier_id
               JOIN supplier_decisions d ON d.score_id = s.score_id
               WHERE p.supplier_id = ? AND s.run_id = ?""",
            (supplier_id, run_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' was not found in the latest scoring run.")
        return dict(row)
    finally:
        conn.close()
