"""
Svitch Compliance Engine API

POST /report/dpdp-dpia    → Generate a DPDP DPIA report
POST /report/rbi-free     → Generate an RBI FREE self-assessment
GET  /report/{id}         → Retrieve a previously generated report (JSON)
GET  /report/{id}/html    → Retrieve HTML version (print as PDF)
"""

from __future__ import annotations

import os
import sys
import uuid
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "agent-tracer"))
os.environ.setdefault("SVITCH_DB_PATH", os.path.join(ROOT, "svitch_audit.db"))

from report_gen import generate_dpia, generate_rbi_free
from report_gen.base import ProcessingActivity
from render_html import render_dpia, render_rbi_free

app = FastAPI(
    title="Svitch Compliance Engine",
    description="Auto-generate DPDP DPIA and RBI FREE compliance reports from agent telemetry.",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory report store (replace with Supabase / Postgres in production)
_report_store: dict[str, dict] = {}


# ── Request models ─────────────────────────────────────────────────────────────

class ActivityInput(BaseModel):
    name: str
    purpose: str
    legal_basis: str = "Consent (DPDP Section 7)"
    data_categories: list[str] = []
    data_principals: str = "customers"
    retention_period: str = "As per RBI guidelines (5–7 years)"
    third_party_processors: list[str] = []
    cross_border_transfer: bool = False


class DPIARequest(BaseModel):
    organisation: str
    prepared_by: str
    period_start: str                       # YYYY-MM-DD
    period_end: str
    processing_activities: list[ActivityInput]
    run_ids: list[str] = []
    dpo_name: str = ""
    is_sdf: bool = True


class RBIFREERequest(BaseModel):
    organisation: str
    prepared_by: str
    period_start: str
    period_end: str
    run_ids: list[str] = []
    manual_overrides: dict[str, str] = {}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0", "reports_generated": len(_report_store)}


@app.post("/report/dpdp-dpia")
def generate_dpia_report(req: DPIARequest):
    activities = [ProcessingActivity(**a.model_dump()) for a in req.processing_activities]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report = generate_dpia(
        organisation=req.organisation,
        prepared_by=req.prepared_by,
        period_start=req.period_start,
        period_end=req.period_end,
        generated_at=now,
        processing_activities=activities,
        run_ids=req.run_ids,
        dpo_name=req.dpo_name,
        is_sdf=req.is_sdf,
    )

    report_dict = json.loads(report.to_json())
    report_id   = report_dict["meta"]["report_id"]
    report_dict["_type"] = "dpia"
    _report_store[report_id] = report_dict

    return JSONResponse(content={
        "report_id": report_id,
        "compliance_score_pct": report_dict["summary"]["overall_compliance_score_pct"],
        "overall_risk": report_dict["summary"]["overall_risk_level"],
        "approval_status": report_dict.get("approval_status", "pending"),
        "html_url": f"/report/{report_id}/html",
        "json_url": f"/report/{report_id}",
        "report": report_dict,
    })


@app.post("/report/rbi-free")
def generate_rbi_report(req: RBIFREERequest):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report = generate_rbi_free(
        organisation=req.organisation,
        prepared_by=req.prepared_by,
        period_start=req.period_start,
        period_end=req.period_end,
        generated_at=now,
        run_ids=req.run_ids,
        manual_overrides=req.manual_overrides,
    )

    report_dict = json.loads(report.to_json())
    report_id   = report_dict["meta"]["report_id"]
    report_dict["_type"] = "rbi_free"
    _report_store[report_id] = report_dict

    return JSONResponse(content={
        "report_id": report_id,
        "overall_score_pct": report_dict["summary"]["overall_score_pct"],
        "pillar_scores": report_dict["summary"]["pillar_scores"],
        "html_url": f"/report/{report_id}/html",
        "json_url": f"/report/{report_id}",
        "report": report_dict,
    })


@app.get("/report/{report_id}")
def get_report(report_id: str):
    r = _report_store.get(report_id)
    if not r:
        raise HTTPException(404, f"Report {report_id} not found.")
    return JSONResponse(content=r)


@app.get("/report/{report_id}/html", response_class=HTMLResponse)
def get_report_html(report_id: str):
    r = _report_store.get(report_id)
    if not r:
        raise HTTPException(404, f"Report {report_id} not found.")
    if r.get("_type") == "dpia":
        return HTMLResponse(content=render_dpia(r))
    return HTMLResponse(content=render_rbi_free(r))
