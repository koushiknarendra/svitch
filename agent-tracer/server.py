"""
Svitch Agent Tracer API

GET  /health                   — Service health
GET  /runs                     — List recent runs (all agents or ?agent_id=)
GET  /runs/{run_id}            — All events for a run
GET  /runs/{run_id}/verify     — Verify hash chain for a run
POST /runs/{run_id}/events     — Append an event to a run
GET  /agents                   — List agents with run counts
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import uuid

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Use /tmp on Vercel (read-only filesystem outside /tmp)
os.environ.setdefault("SVITCH_DB_PATH", "/tmp/svitch_audit.db")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from svitch_tracer.storage import db as store

app = FastAPI(
    title="Svitch Agent Tracer",
    description="Hash-chained audit log for AI agent decisions.",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store.init_db()


class EventRequest(BaseModel):
    agent_id: str
    event_type: str           # llm_call | tool_call | decision | human_checkpoint | data_access
    data: dict
    pii_types: list[str] = []
    pii_redacted: bool = False
    human_approved: Optional[bool] = None


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/runs")
def list_runs(agent_id: Optional[str] = None, limit: int = 50):
    """List recent runs with summary stats."""
    conn = store._get_sqlite_conn()
    if agent_id:
        rows = conn.execute("""
            SELECT run_id, agent_id,
                   MIN(timestamp_ms) as started_at,
                   MAX(timestamp_ms) as last_event_at,
                   COUNT(*) as event_count,
                   SUM(CASE WHEN pii_types != '[]' THEN 1 ELSE 0 END) as pii_events,
                   SUM(CASE WHEN human_approved IS NOT NULL THEN 1 ELSE 0 END) as human_checkpoints
            FROM audit_log WHERE agent_id = ?
            GROUP BY run_id
            ORDER BY started_at DESC LIMIT ?
        """, (agent_id, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT run_id, agent_id,
                   MIN(timestamp_ms) as started_at,
                   MAX(timestamp_ms) as last_event_at,
                   COUNT(*) as event_count,
                   SUM(CASE WHEN pii_types != '[]' THEN 1 ELSE 0 END) as pii_events,
                   SUM(CASE WHEN human_approved IS NOT NULL THEN 1 ELSE 0 END) as human_checkpoints
            FROM audit_log
            GROUP BY run_id
            ORDER BY started_at DESC LIMIT ?
        """, (limit,)).fetchall()

    return {
        "count": len(rows),
        "runs": [
            {
                "run_id": r["run_id"],
                "agent_id": r["agent_id"],
                "started_at_ms": r["started_at"],
                "last_event_at_ms": r["last_event_at"],
                "duration_ms": r["last_event_at"] - r["started_at"],
                "event_count": r["event_count"],
                "pii_events": r["pii_events"],
                "human_checkpoints": r["human_checkpoints"],
            }
            for r in rows
        ],
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    records = store.get_run(run_id)
    if not records:
        raise HTTPException(404, f"Run {run_id} not found")
    return {
        "run_id": run_id,
        "agent_id": records[0].agent_id,
        "event_count": len(records),
        "events": [
            {
                "id": r.id,
                "seq": i + 1,
                "event_type": r.event_type,
                "timestamp_ms": r.timestamp_ms,
                "data": r.data,
                "pii_types": r.pii_types,
                "pii_redacted": r.pii_redacted,
                "human_approved": r.human_approved,
                "record_hash": r.record_hash[:16] + "…",
            }
            for i, r in enumerate(records)
        ],
    }


@app.get("/runs/{run_id}/verify")
def verify_run(run_id: str):
    valid, err = store.verify_chain(run_id)
    return {"run_id": run_id, "valid": valid, "error": err}


@app.post("/runs/{run_id}/events")
def append_event(run_id: str, req: EventRequest):
    record = store.append(
        run_id=run_id,
        agent_id=req.agent_id,
        event_type=req.event_type,
        data=req.data,
        pii_types=req.pii_types,
        pii_redacted=req.pii_redacted,
        human_approved=req.human_approved,
    )
    return {
        "id": record.id,
        "run_id": run_id,
        "record_hash": record.record_hash,
        "timestamp_ms": record.timestamp_ms,
    }


@app.get("/agents")
def list_agents():
    conn = store._get_sqlite_conn()
    rows = conn.execute("""
        SELECT agent_id,
               COUNT(DISTINCT run_id) as run_count,
               COUNT(*) as event_count,
               MAX(timestamp_ms) as last_seen_ms
        FROM audit_log
        GROUP BY agent_id
        ORDER BY last_seen_ms DESC
    """).fetchall()
    return {
        "count": len(rows),
        "agents": [
            {
                "agent_id": r["agent_id"],
                "run_count": r["run_count"],
                "event_count": r["event_count"],
                "last_seen_ms": r["last_seen_ms"],
            }
            for r in rows
        ],
    }
