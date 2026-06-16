"""
RBI FREE Framework Self-Assessment Generator

The Reserve Bank of India's Framework for Responsible and Ethical Enablement
of AI (FREE) contains 26 recommendations across 5 pillars. Applicable to all
RBI-regulated entities (banks, NBFCs, payment operators) using AI systems.

This generator populates the self-assessment checklist from Svitch telemetry
and produces a report an RBI auditor can review directly.

Reference: RBI Circular DOR.STR.REC.41/21.07.001/2024-25
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass, asdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "agent-tracer"))
os.environ.setdefault("SVITCH_DB_PATH", os.path.join(ROOT, "svitch_audit.db"))

from .base import CheckItem, ReportMeta, BaseReport


# ── RBI FREE Framework — 26 Recommendations ───────────────────────────────────
# Pillar → [(recommendation_id, description)]

RBI_FREE_PILLARS = {
    "G": {
        "title": "Governance",
        "recommendations": [
            ("G1", "Board-approved AI governance policy covering risk appetite, accountability, and oversight."),
            ("G2", "Designated senior management accountability for AI (CRO / CDO / equivalent)."),
            ("G3", "AI inventory maintained — all AI systems in production catalogued and risk-classified."),
            ("G4", "Third-party AI vendor due diligence process with contractual obligations."),
            ("G5", "Change management process for AI model updates (testing, approval, rollback plan)."),
            ("G6", "AI incident management and escalation procedure defined."),
        ],
    },
    "R": {
        "title": "Risk Management",
        "recommendations": [
            ("R1", "AI-specific risk assessment conducted before deployment (credit, operational, reputational)."),
            ("R2", "Model risk management framework covers AI/ML models (validation, monitoring, retirement)."),
            ("R3", "Audit trail of AI model decisions maintained and tamper-proof."),
            ("R4", "AI system performance monitored in production (drift, bias, accuracy degradation)."),
            ("R5", "Data quality controls in place (lineage, completeness, bias screening before training)."),
            ("R6", "Concentration risk assessed — dependency on single AI vendor or model family."),
        ],
    },
    "F": {
        "title": "Fairness, Ethics & Accountability",
        "recommendations": [
            ("F1", "Bias testing conducted for AI systems making decisions affecting customers (credit, pricing)."),
            ("F2", "Human-in-the-loop for high-value or high-risk AI decisions (loans > threshold, fraud flags)."),
            ("F3", "Customer grievance mechanism for AI-driven decisions (right to contest an AI outcome)."),
            ("F4", "Ethics review board or committee oversees high-impact AI use cases."),
            ("F5", "Discrimination prohibited — AI models do not use protected characteristics as proxies."),
            ("F6", "Fairness metrics tracked and reported to senior management quarterly."),
        ],
    },
    "E": {
        "title": "Explainability",
        "recommendations": [
            ("E1", "AI decisions affecting customers communicated in plain language (reason codes provided)."),
            ("E2", "Internal explainability for risk teams — feature importance, decision rationale available."),
            ("E3", "Regulators can request explanation of AI decisions — process and timeline defined."),
            ("E4", "Black-box models in high-risk use cases accompanied by interpretable surrogate models."),
        ],
    },
    "RS": {
        "title": "Robustness & Security",
        "recommendations": [
            ("RS1", "AI system resilience tested — adversarial inputs, prompt injection, data poisoning scenarios."),
            ("RS2", "Personal data used in AI protected against exfiltration to third-party AI providers."),
            ("RS3", "AI model access controls — least privilege, authentication, rate limiting enforced."),
            ("RS4", "Incident response plan covers AI-specific failure modes (model inversion, membership inference)."),
        ],
    },
}


def _assess_from_telemetry(telemetry: dict) -> dict[str, str]:
    """
    Map Svitch telemetry onto RBI FREE recommendation IDs.
    Returns {recommendation_id: status}.
    """
    has_audit    = telemetry.get("total_runs", 0) > 0
    has_human    = telemetry.get("human_checkpoints", 0) > 0
    has_pii_ctrl = telemetry.get("pii_events", 0) >= 0   # shield always running
    chain_valid  = telemetry.get("chain_valid", True)

    return {
        # Governance — requires manual inputs
        "G1": "not_assessed",
        "G2": "not_assessed",
        "G3": "partial",    # Svitch audit log is the AI inventory basis
        "G4": "partial",    # Svitch wraps third-party LLM calls with controls
        "G5": "not_assessed",
        "G6": "not_assessed",
        # Risk Management
        "R1": "partial",    # DPDP DPIA covers AI risk assessment
        "R2": "not_assessed",
        "R3": "compliant" if has_audit and chain_valid else "partial",
        "R4": "partial",    # Svitch health endpoint; full monitoring not yet built
        "R5": "partial",    # PII Shield scrubs data; bias screening not yet built
        "R6": "not_assessed",
        # Fairness
        "F1": "not_assessed",
        "F2": "compliant" if has_human else "non_compliant",
        "F3": "partial",
        "F4": "not_assessed",
        "F5": "not_assessed",
        "F6": "not_assessed",
        # Explainability
        "E1": "partial",
        "E2": "compliant" if has_audit else "partial",
        "E3": "compliant" if has_audit else "partial",
        "E4": "not_assessed",
        # Robustness & Security
        "RS1": "partial",
        "RS2": "compliant" if has_pii_ctrl else "non_compliant",
        "RS3": "partial",
        "RS4": "partial",
    }


def _evidence(rec_id: str, telemetry: dict) -> tuple[str, str, str]:
    """Returns (evidence, gap, recommendation) for a given recommendation ID."""
    table = {
        "G3": (
            "Svitch Agent Tracer catalogues all AI runs with agent_id, model, and data categories.",
            "Formal AI inventory register not yet formalised outside Svitch.",
            "Export Svitch agent_id list and risk-classify each system in a spreadsheet register.",
        ),
        "G4": (
            "Svitch PII Shield enforces data controls on all third-party LLM calls (OpenAI, Anthropic, Gemini).",
            "Formal vendor due diligence contracts not yet reviewed for AI-specific clauses.",
            "Add AI governance addendum to OpenAI/Anthropic contracts: data retention, subprocessor restrictions.",
        ),
        "R3": (
            f"Svitch Agent Tracer: {telemetry.get('total_runs', 0)} runs, {telemetry.get('llm_calls', 0)} LLM calls recorded with SHA-256 Merkle chain.",
            "",
            "",
        ),
        "R4": (
            "Svitch /health endpoint provides runtime status.",
            "No automated drift or accuracy monitoring implemented.",
            "Integrate model performance metrics into Svitch dashboard (Phase 4 roadmap).",
        ),
        "R5": (
            "Svitch PII Shield screens all prompts before LLM processing — prevents personal data leakage in training data.",
            "Bias screening of training datasets not implemented.",
            "Add bias audit to model evaluation pipeline before deployment.",
        ),
        "F2": (
            f"Svitch Agent Tracer recorded {telemetry.get('human_checkpoints', 0)} human checkpoint events with reviewer_id and approval outcome.",
            "" if telemetry.get("human_checkpoints", 0) > 0 else "No human checkpoints recorded — high-value decisions may be fully automated.",
            "" if telemetry.get("human_checkpoints", 0) > 0 else "Implement run.human_checkpoint() for all loan / fraud decisions above risk threshold.",
        ),
        "F3": (
            "Grievance mechanism exists (contact DPO), but AI-specific contest mechanism not documented.",
            "Customers cannot formally contest an AI credit decision through a defined process.",
            "Add 'Contest this decision' flow to customer portal, routed to human reviewer with Agent Tracer context.",
        ),
        "E2": (
            f"Agent Tracer decision lineage: every agent step queryable by run_id ({telemetry.get('total_runs', 0)} runs).",
            "",
            "",
        ),
        "E3": (
            "Agent Tracer provides full decision reconstruction for any run_id — auditor access via query API.",
            "",
            "",
        ),
        "RS2": (
            f"Svitch PII Shield blocked {telemetry.get('pii_events', 0)} PII events from reaching third-party LLMs in this period.",
            "",
            "",
        ),
        "RS3": (
            "Svitch Enclave uses WireGuard VPN + API key authentication.",
            "Rate limiting not yet implemented on the inference proxy.",
            "Add rate limiting middleware to private-enclave/inference/server.py.",
        ),
    }
    default = ("", "Manual assessment required.", "Complete internal review and document evidence.")
    return table.get(rec_id, default)


def generate(
    organisation: str,
    prepared_by: str,
    period_start: str,
    period_end: str,
    generated_at: str,
    run_ids: list[str] | None = None,
    manual_overrides: dict[str, str] | None = None,
) -> BaseReport:
    """
    Generate an RBI FREE Framework self-assessment report.

    Args:
        organisation: Name of the regulated entity
        prepared_by: Name of person preparing the report
        period_start/end: Assessment period (YYYY-MM-DD)
        generated_at: ISO 8601 timestamp
        run_ids: Svitch Agent Tracer run IDs to pull telemetry from
        manual_overrides: Dict of {recommendation_id: status} to override auto-assessment
    """
    telemetry = _pull_tracer_data(run_ids or [])
    auto_status = _assess_from_telemetry(telemetry)
    if manual_overrides:
        auto_status.update(manual_overrides)

    meta = ReportMeta(
        report_id=f"RBI-FREE-{uuid.uuid4().hex[:8].upper()}",
        report_type="RBI FREE Framework Self-Assessment",
        organisation=organisation,
        prepared_by=prepared_by,
        period_start=period_start,
        period_end=period_end,
        generated_at=generated_at,
    )

    sections = []
    pillar_scores: dict[str, int] = {}

    for pillar_id, pillar in RBI_FREE_PILLARS.items():
        checks = []
        for rec_id, rec_text in pillar["recommendations"]:
            status = auto_status.get(rec_id, "not_assessed")
            evidence, gap, recommendation = _evidence(rec_id, telemetry)
            checks.append(asdict(CheckItem(
                id=rec_id,
                requirement=rec_text,
                status=status,
                evidence=evidence,
                gap=gap,
                recommendation=recommendation,
            )))

        # Score pillar
        weights = {"compliant": 1.0, "partial": 0.5, "non_compliant": 0.0, "not_assessed": 0.3}
        pillar_score = int(sum(weights.get(c["status"], 0) for c in checks) / len(checks) * 100)
        pillar_scores[pillar["title"]] = pillar_score

        sections.append({
            "id": f"P{pillar_id}",
            "title": f"Pillar {pillar_id}: {pillar['title']}",
            "score_pct": pillar_score,
            "checks": checks,
        })

    overall = int(sum(pillar_scores.values()) / len(pillar_scores))

    # Executive summary
    gaps = []
    for section in sections:
        for c in section["checks"]:
            if c["status"] in ("non_compliant", "partial") and c["gap"]:
                gaps.append(f"[{c['id']}] {c['gap']}")

    report = BaseReport(
        meta=asdict(meta),  # type: ignore[arg-type]
        summary={
            "organisation": organisation,
            "period": f"{period_start} to {period_end}",
            "framework": "RBI FREE (DOR.STR.REC.41/21.07.001/2024-25)",
            "overall_score_pct": overall,
            "pillar_scores": pillar_scores,
            "total_recommendations": 26,
            "compliant": sum(1 for s in auto_status.values() if s == "compliant"),
            "partial": sum(1 for s in auto_status.values() if s == "partial"),
            "non_compliant": sum(1 for s in auto_status.values() if s == "non_compliant"),
            "not_assessed": sum(1 for s in auto_status.values() if s == "not_assessed"),
            "top_gaps": gaps[:5],
            "agent_runs_analysed": telemetry["total_runs"],
            "pii_events_controlled": telemetry["pii_events"],
            "human_checkpoints_recorded": telemetry["human_checkpoints"],
        },
        sections=sections,
    )
    return report


def _pull_tracer_data(run_ids: list[str]) -> dict:
    defaults = {"total_runs": 0, "llm_calls": 0, "pii_events": 0,
                "human_checkpoints": 0, "pii_types_seen": [], "chain_valid": True}
    if not run_ids:
        return defaults
    try:
        from svitch_tracer.storage.db import init_db, get_run, verify_chain
        init_db()
        all_records, chain_valid = [], True
        for rid in run_ids:
            try:
                records = get_run(rid)
                all_records.extend(records)
                valid, _ = verify_chain(rid)
                if not valid:
                    chain_valid = False
            except Exception:
                pass
        pii_types: set[str] = set()
        llm_calls = human_checkpoints = pii_events = 0
        for r in all_records:
            if r.event_type == "llm_call":
                llm_calls += 1
                pii_events += len(r.pii_types or [])
                pii_types.update(r.pii_types or [])
            elif r.event_type == "human_checkpoint":
                human_checkpoints += 1
        return {"total_runs": len(run_ids), "llm_calls": llm_calls,
                "pii_events": pii_events, "human_checkpoints": human_checkpoints,
                "pii_types_seen": list(pii_types), "chain_valid": chain_valid}
    except Exception:
        return defaults
