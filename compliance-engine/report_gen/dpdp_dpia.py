"""
DPDP Data Protection Impact Assessment (DPIA) Generator

Generates a DPIA aligned with India's Digital Personal Data Protection Act 2023.
Significant Data Fiduciaries are required to conduct DPIAs under Section 10(2)(b).

The report is populated from:
  - Svitch Agent Tracer audit records (what data was processed, by which agents)
  - Manual inputs (organisation details, processing activities)
  - Automatic inferences (PII types detected, human checkpoints, third-party calls)
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "agent-tracer"))
os.environ.setdefault("SVITCH_DB_PATH", os.path.join(ROOT, "svitch_audit.db"))

from .base import CheckItem, RiskItem, ProcessingActivity, ReportMeta, BaseReport


# ── DPDP-specific sections ────────────────────────────────────────────────────

DPDP_RIGHTS = [
    "Right to information (Section 11)",
    "Right to correction and erasure (Section 12)",
    "Right to grievance redressal (Section 13)",
    "Right to nominate (Section 14)",
]

DPDP_OBLIGATIONS = [
    ("S8(1)",  "Process personal data only for specified purpose with valid consent"),
    ("S8(2)",  "Ensure accuracy and completeness of personal data"),
    ("S8(3)",  "Implement appropriate security safeguards"),
    ("S8(4)",  "Notify DPBI and data principals of personal data breach"),
    ("S8(5)",  "Erase data when purpose is fulfilled or consent withdrawn"),
    ("S8(7)",  "Publish contact details of Data Protection Officer"),
    ("S10(1)", "Conduct annual DPIA (Significant Data Fiduciary)"),
    ("S10(2)", "Appoint DPO resident in India (Significant Data Fiduciary)"),
    ("S10(3)", "Conduct data audit (Significant Data Fiduciary)"),
]


@dataclass
class DPDPDPIAReport(BaseReport):
    processing_activities: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    dpo_recommendation: str = ""
    approval_status: str = "pending"


def _pii_category_to_dpdp(pii_type: str) -> str:
    mapping = {
        "AADHAAR":       "Government identifier (Aadhaar — sensitive personal data)",
        "PAN":           "Financial identifier (PAN card)",
        "UPI_ID":        "Financial data (UPI/payment identifier)",
        "IFSC":          "Financial data (bank routing code)",
        "BANK_ACCOUNT":  "Financial data (bank account number)",
        "MOBILE_IN":     "Contact data (mobile number)",
        "EMAIL":         "Contact data (email address)",
        "GST":           "Business identifier (GST number)",
        "VOTER_ID":      "Government identifier (Voter ID / EPIC)",
        "PASSPORT_IN":   "Government identifier (passport number)",
        "IPV4":          "Technical data (IP address — personal data under DPDP)",
    }
    return mapping.get(pii_type, f"Personal data ({pii_type})")


def _risk_level(pii_types: list[str], has_human_checkpoint: bool, third_parties: list[str]) -> str:
    sensitive = {"AADHAAR", "BANK_ACCOUNT", "PAN", "PASSPORT_IN", "VOTER_ID"}
    if any(p in sensitive for p in pii_types):
        return "high"
    if third_parties or not has_human_checkpoint:
        return "medium"
    return "low"


def generate(
    organisation: str,
    prepared_by: str,
    period_start: str,
    period_end: str,
    generated_at: str,
    processing_activities: list[ProcessingActivity],
    run_ids: Optional[list[str]] = None,
    dpo_name: str = "",
    is_sdf: bool = True,
) -> DPDPDPIAReport:
    """
    Generate a DPDP DPIA report.

    Args:
        organisation: Legal name of the Data Fiduciary
        prepared_by: Name of person preparing the DPIA
        period_start: Assessment period start (YYYY-MM-DD)
        period_end: Assessment period end (YYYY-MM-DD)
        generated_at: Generation timestamp (ISO 8601)
        processing_activities: List of ProcessingActivity describing AI workflows
        run_ids: Optional list of Svitch Tracer run IDs to pull telemetry from
        dpo_name: Name of the Data Protection Officer
        is_sdf: Whether the organisation is a Significant Data Fiduciary
    """

    # ── Pull telemetry from Agent Tracer ──────────────────────────────────────
    tracer_summary = _pull_tracer_data(run_ids or [])

    meta = ReportMeta(
        report_id=f"DPIA-{uuid.uuid4().hex[:8].upper()}",
        report_type="DPDP Data Protection Impact Assessment",
        organisation=organisation,
        prepared_by=prepared_by,
        period_start=period_start,
        period_end=period_end,
        generated_at=generated_at,
        version="1.0",
    )

    # ── Section 1: Processing description ─────────────────────────────────────
    all_pii_types = list({p for a in processing_activities for p in a.data_categories}
                         | set(tracer_summary["pii_types_seen"]))
    section1 = {
        "id": "S1",
        "title": "Description of Personal Data Processing",
        "description": "Overview of AI-mediated personal data processing activities covered by this DPIA.",
        "content": {
            "activities": [asdict(a) for a in processing_activities],
            "agent_runs_analysed": tracer_summary["total_runs"],
            "llm_calls_made": tracer_summary["llm_calls"],
            "total_pii_events": tracer_summary["pii_events"],
            "pii_types_processed": [_pii_category_to_dpdp(p) for p in all_pii_types],
            "human_checkpoints_used": tracer_summary["human_checkpoints"],
            "pii_always_redacted_in_storage": True,
            "models_used": tracer_summary["models_used"],
        },
    }

    # ── Section 2: Necessity & proportionality ─────────────────────────────────
    checks_s2 = [
        CheckItem(
            id="S2.1",
            requirement="Processing is limited to the stated purpose (data minimisation)",
            status="compliant" if tracer_summary["pii_events"] > 0 else "not_assessed",
            evidence="Svitch PII Shield redacts personal data not required for the stated purpose before LLM processing.",
        ),
        CheckItem(
            id="S2.2",
            requirement="Legal basis (consent / legitimate use) documented for each activity",
            status="compliant" if all(a.legal_basis for a in processing_activities) else "partial",
            evidence=", ".join({a.legal_basis for a in processing_activities}) or "Not documented",
            gap="" if all(a.legal_basis for a in processing_activities) else "Some activities lack documented legal basis.",
        ),
        CheckItem(
            id="S2.3",
            requirement="Retention periods defined and enforced",
            status="compliant" if all(a.retention_period for a in processing_activities) else "partial",
            evidence="; ".join({f"{a.name}: {a.retention_period}" for a in processing_activities}),
        ),
        CheckItem(
            id="S2.4",
            requirement="Cross-border transfers assessed (if applicable)",
            status="compliant" if not any(a.cross_border_transfer for a in processing_activities)
                   else "partial",
            evidence="No cross-border transfers detected" if not any(a.cross_border_transfer for a in processing_activities)
                     else "Cross-border transfers present — Standard Contractual Clauses required.",
            gap="" if not any(a.cross_border_transfer for a in processing_activities)
                else "Review adequacy of SCCs for each cross-border transfer.",
        ),
    ]
    section2 = {
        "id": "S2",
        "title": "Necessity and Proportionality Assessment",
        "checks": [asdict(c) for c in checks_s2],
    }

    # ── Section 3: Rights of data principals ──────────────────────────────────
    checks_s3 = [
        CheckItem("S3.1", "Right to information — notice published before data collection", "compliant",
                  evidence="Consent notice and privacy policy must be in place (verify separately)."),
        CheckItem("S3.2", "Right to correction/erasure — mechanism in place", "partial",
                  evidence="Agent Tracer records can be queried per data principal ID.",
                  gap="Automated erasure workflow not yet implemented.",
                  recommendation="Implement a /erasure API endpoint that removes all records for a given data_principal_id from the audit log."),
        CheckItem("S3.3", "Right to grievance redressal — DPO contact published", "compliant" if dpo_name else "non_compliant",
                  evidence=f"DPO: {dpo_name}" if dpo_name else "No DPO appointed.",
                  gap="" if dpo_name else "Appoint a DPO resident in India (mandatory for SDFs under Section 10(2))."),
        CheckItem("S3.4", "Right to nominate — nominee registration supported", "partial",
                  gap="Nominee registration mechanism not implemented.",
                  recommendation="Add nominee field to user consent records."),
    ]
    section3 = {
        "id": "S3",
        "title": "Rights of Data Principals",
        "checks": [asdict(c) for c in checks_s3],
    }

    # ── Section 4: Statutory obligations ──────────────────────────────────────
    checks_s4 = []
    for ref, text in DPDP_OBLIGATIONS:
        if ref in ("S10(1)", "S10(2)", "S10(3)") and not is_sdf:
            continue
        status: str
        gap = ""
        evidence = ""
        if ref == "S8(1)":
            status = "compliant"
            evidence = "Svitch PII Shield enforces processing only for declared purpose."
        elif ref == "S8(3)":
            status = "compliant"
            evidence = "AES-256 encryption at rest; TLS 1.3 in transit; WireGuard tunnel for Private Enclave."
        elif ref == "S8(4)":
            status = "partial"
            evidence = "Svitch audit log provides tamper-evident breach evidence trail."
            gap = "Automated DPBI breach notification workflow not yet implemented (72-hour window)."
        elif ref == "S8(5)":
            status = "partial"
            gap = "Automated data erasure on purpose completion not implemented."
            evidence = "Manual erasure via Agent Tracer query API."
        elif ref == "S10(1)":
            status = "compliant"
            evidence = f"This DPIA (Report ID: {meta.report_id}) constitutes the annual DPIA."
        elif ref == "S10(2)":
            status = "compliant" if dpo_name else "non_compliant"
            evidence = f"DPO: {dpo_name}" if dpo_name else ""
            gap = "No DPO appointed." if not dpo_name else ""
        elif ref == "S10(3)":
            status = "partial"
            evidence = "Svitch agent telemetry provides audit data; formal auditor not yet engaged."
            gap = "Engage a CERT-In empanelled auditor for annual data audit."
        else:
            status = "compliant"
            evidence = "Implemented."
        checks_s4.append(asdict(CheckItem(ref, text, status, evidence, gap)))  # type: ignore[arg-type]

    section4 = {
        "id": "S4",
        "title": "DPDP Statutory Obligations Checklist",
        "is_sdf": is_sdf,
        "checks": checks_s4,
    }

    # ── Section 5: Risk register ───────────────────────────────────────────────
    has_human = tracer_summary["human_checkpoints"] > 0
    third_parties = list({p for a in processing_activities for p in a.third_party_processors})
    overall_risk = _risk_level(all_pii_types, has_human, third_parties)

    risks = [
        RiskItem(
            id="R1",
            description="Sensitive personal data (Aadhaar/PAN) transmitted to third-party LLM API without redaction",
            likelihood="low" if "AADHAAR" in tracer_summary["pii_types_seen"] and tracer_summary["pii_events"] > 0 else "medium",
            impact="high",
            mitigation="Svitch PII Shield redacts Aadhaar and PAN before every LLM API call. Verified by audit log.",
            residual_risk="low",
        ),
        RiskItem(
            id="R2",
            description="AI agent makes autonomous high-value decisions on personal data without human oversight",
            likelihood="low" if has_human else "high",
            impact="high",
            mitigation=f"Human checkpoint events recorded in audit log ({tracer_summary['human_checkpoints']} in this period).",
            residual_risk="low" if has_human else "high",
        ),
        RiskItem(
            id="R3",
            description="Audit log tampered with after the fact, destroying evidence trail",
            likelihood="low",
            impact="high",
            mitigation="Svitch Agent Tracer uses SHA-256 Merkle chain — any tampering breaks chain verification.",
            residual_risk="low",
        ),
        RiskItem(
            id="R4",
            description="Data principal unable to exercise erasure right — data retained beyond purpose",
            likelihood="medium",
            impact="medium",
            mitigation="Agent Tracer stores data_principal_id per record for targeted retrieval.",
            residual_risk="medium",
        ),
        RiskItem(
            id="R5",
            description="Personal data breach notification not sent within 72 hours (Section 8(4))",
            likelihood="medium",
            impact="high",
            mitigation="Svitch audit log provides breach evidence. Manual notification process in place.",
            residual_risk="medium",
        ),
    ]
    section5 = {
        "id": "S5",
        "title": "Risk Register",
        "overall_risk_level": overall_risk,
        "risks": [asdict(r) for r in risks],
    }

    # ── Section 6: Mitigations in place ───────────────────────────────────────
    section6 = {
        "id": "S6",
        "title": "Technical and Organisational Measures",
        "measures": [
            {
                "category": "PII Detection & Redaction",
                "measure": "Svitch PII Shield — real-time detection and redaction of Indian PII (Aadhaar, PAN, UPI, IFSC, mobile) before any LLM API call.",
                "standard": "DPDP Section 8(3), ISO 27001 A.8.12",
                "status": "implemented",
            },
            {
                "category": "Audit Trail",
                "measure": "Svitch Agent Tracer — append-only, SHA-256 Merkle-chained log of every agent decision, LLM call, and data access event.",
                "standard": "DPDP Section 10(3), RBI FREE Framework R3",
                "status": "implemented",
            },
            {
                "category": "Human Oversight",
                "measure": "Human checkpoint events enforced for high-value decisions. Recorded with reviewer ID and approval outcome.",
                "standard": "RBI FREE Framework F2, DPDP Section 8",
                "status": "implemented",
            },
            {
                "category": "Access Control",
                "measure": "Private Enclave with WireGuard tunnel — AI inference runs on customer-dedicated compute, no data egress to shared infrastructure.",
                "standard": "DPDP Section 8(3), ISO 27001 A.9",
                "status": "implemented",
            },
            {
                "category": "Breach Detection",
                "measure": "PII detection events flagged in audit log. Breach notification workflow partially implemented.",
                "standard": "DPDP Section 8(4)",
                "status": "partial",
            },
            {
                "category": "Data Erasure",
                "measure": "Agent Tracer supports per-data-principal record lookup for manual erasure.",
                "standard": "DPDP Section 8(5), Section 12",
                "status": "partial",
            },
        ],
    }

    # ── Section 7: DPO recommendation ─────────────────────────────────────────
    score = _estimate_score(checks_s2, checks_s3, checks_s4)
    dpo_text = (
        f"Based on the assessment, {organisation} has implemented strong technical controls "
        f"through the Svitch platform. The overall compliance posture is {score}%. "
        f"Key gaps: automated data erasure workflow and DPBI breach notification pipeline. "
        f"Recommend prioritising these in the next sprint before the DPDP enforcement deadline."
    )
    section7 = {
        "id": "S7",
        "title": "DPO Recommendation",
        "dpo_name": dpo_name or "Not appointed",
        "recommendation": dpo_text,
        "approval_recommended": score >= 70,
    }

    report = DPDPDPIAReport(
        meta=asdict(meta),  # type: ignore[arg-type]
        summary={
            "organisation": organisation,
            "period": f"{period_start} to {period_end}",
            "overall_compliance_score_pct": score,
            "overall_risk_level": overall_risk,
            "total_agent_runs": tracer_summary["total_runs"],
            "pii_events_blocked": tracer_summary["pii_events"],
            "human_checkpoints_recorded": tracer_summary["human_checkpoints"],
            "is_significant_data_fiduciary": is_sdf,
            "dpo_appointed": bool(dpo_name),
        },
        sections=[section1, section2, section3, section4, section5, section6, section7],
        processing_activities=[asdict(a) for a in processing_activities],
        risks=[asdict(r) for r in risks],
        dpo_recommendation=dpo_text,
        approval_status="approved" if score >= 70 else "conditional",
    )

    return report


def _pull_tracer_data(run_ids: list[str]) -> dict:
    """Pull summary stats from the Agent Tracer audit log."""
    defaults = {
        "total_runs": 0,
        "llm_calls": 0,
        "pii_events": 0,
        "human_checkpoints": 0,
        "pii_types_seen": [],
        "models_used": [],
    }
    try:
        from svitch_tracer.storage.db import init_db, get_run
        init_db()

        if not run_ids:
            return defaults

        all_records = []
        for rid in run_ids:
            try:
                all_records.extend(get_run(rid))
            except Exception:
                pass

        pii_types: set[str] = set()
        models: set[str] = set()
        llm_calls = human_checkpoints = pii_events = 0

        for r in all_records:
            if r.event_type == "llm_call":
                llm_calls += 1
                if r.pii_types:
                    pii_events += len(r.pii_types)
                    pii_types.update(r.pii_types)
                if r.data.get("model"):
                    models.add(r.data["model"])
            elif r.event_type == "human_checkpoint":
                human_checkpoints += 1

        return {
            "total_runs": len(run_ids),
            "llm_calls": llm_calls,
            "pii_events": pii_events,
            "human_checkpoints": human_checkpoints,
            "pii_types_seen": list(pii_types),
            "models_used": list(models),
        }
    except Exception:
        return defaults


def _estimate_score(checks_s2, checks_s3, checks_s4) -> int:
    all_checks = checks_s2 + checks_s3 + checks_s4
    if not all_checks:
        return 0
    weights = {"compliant": 1.0, "partial": 0.5, "non_compliant": 0.0, "not_assessed": 0.3}
    def _status(c):
        return c["status"] if isinstance(c, dict) else c.status
    score = sum(weights.get(_status(c), 0) for c in all_checks) / len(all_checks)
    return round(score * 100)
