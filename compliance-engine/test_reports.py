"""
Compliance Engine tests.
Run: python compliance-engine/test_reports.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent-tracer"))
os.environ["SVITCH_DB_PATH"] = ":memory:"

from report_gen import generate_dpia, generate_rbi_free
from report_gen.base import ProcessingActivity
from render_html import render_dpia, render_rbi_free


def sep(t): print(f"\n{'─'*54}\n  {t}\n{'─'*54}")


# ── Seed agent-tracer data ────────────────────────────────────────────────────
from svitch_tracer import SvitchTracer
from svitch_tracer.storage.db import init_db

init_db()
tracer = SvitchTracer(agent_id="loan-processor-v1", auto_init_db=False)

with tracer.run() as run:
    run.data_access(source="customer_db", fields_accessed=["aadhaar", "pan", "income"],
                    purpose="loan_eligibility_check", data_principal_id="CUST-001")
    run.llm_call(provider="openai", model="gpt-4o",
                 prompt="Summarise loan eligibility for PAN ABCDE1234F Aadhaar 2345 6789 0123",
                 response="Applicant eligible for loan up to ₹25L.")
    run.human_checkpoint(question="Approve ₹20L loan?", approved=True, reviewer_id="OFFICER-42")
    run.decision(reason="CIBIL 780, income verified", outcome="loan_approved", confidence=0.96)
    run_id1 = run.run_id

with tracer.run() as run:
    run.llm_call(provider="anthropic", model="claude-sonnet-4-6",
                 prompt="KYC check for mobile 9876543210 UPI rahul@okicici",
                 response="KYC verified.")
    run_id2 = run.run_id

print(f"\n  Seeded 2 agent runs: {run_id1[:8]}…, {run_id2[:8]}…")

activities = [
    ProcessingActivity(
        name="Loan Eligibility AI",
        purpose="Assess creditworthiness using AI-powered document analysis",
        legal_basis="Consent (DPDP Section 7) + Contractual necessity",
        data_categories=["AADHAAR", "PAN", "BANK_ACCOUNT", "MOBILE_IN"],
        data_principals="retail banking customers",
        retention_period="7 years (RBI mandate)",
        third_party_processors=["OpenAI (redacted prompts only)"],
        cross_border_transfer=True,
    ),
    ProcessingActivity(
        name="KYC Verification AI",
        purpose="Video KYC and document verification via AI",
        legal_basis="Regulatory obligation (RBI KYC Master Direction)",
        data_categories=["AADHAAR", "PASSPORT_IN", "MOBILE_IN", "EMAIL"],
        data_principals="new account applicants",
        retention_period="10 years (KYC norms)",
        third_party_processors=["Anthropic (redacted prompts only)"],
        cross_border_transfer=True,
    ),
]


# ── Test 1: DPDP DPIA ─────────────────────────────────────────────────────────
sep("Test 1: DPDP DPIA generation")

dpia = generate_dpia(
    organisation="Meridian Financial Services Pvt Ltd",
    prepared_by="Priya Sharma, Chief Privacy Officer",
    period_start="2026-04-01",
    period_end="2026-06-30",
    generated_at="2026-06-16T08:00:00Z",
    processing_activities=activities,
    run_ids=[run_id1, run_id2],
    dpo_name="Rahul Mehta",
    is_sdf=True,
)

summary = dpia.summary
print(f"  Report ID          : {dpia.meta['report_id']}")
print(f"  Compliance score   : {summary['overall_compliance_score_pct']}%")
print(f"  Risk level         : {summary['overall_risk_level']}")
print(f"  Approval status    : {dpia.approval_status}")
print(f"  Agent runs pulled  : {summary['total_agent_runs']}")
print(f"  PII events blocked : {summary['pii_events_blocked']}")
print(f"  Human checkpoints  : {summary['human_checkpoints_recorded']}")
print(f"  Sections generated : {len(dpia.sections)}")

assert dpia.meta["report_id"].startswith("DPIA-")
assert 0 < summary["overall_compliance_score_pct"] <= 100
assert summary["total_agent_runs"] == 2
assert summary["pii_events_blocked"] > 0
assert summary["human_checkpoints_recorded"] == 1
assert len(dpia.sections) == 7
print("  PASS — DPIA generated correctly")


# ── Test 2: DPIA → HTML ───────────────────────────────────────────────────────
sep("Test 2: DPDP DPIA → HTML rendering")
import json
dpia_dict = json.loads(dpia.to_json())
dpia_dict["_type"] = "dpia"
html = render_dpia(dpia_dict)

assert "<!DOCTYPE html>" in html
assert "Meridian Financial Services" in html
assert "DPDP" in html
assert "AADHAAR" in html or "Aadhaar" in html
assert str(summary["overall_compliance_score_pct"]) + "%" in html
print(f"  HTML length : {len(html):,} chars")
print("  PASS — HTML renders correctly")

out_path = "/tmp/svitch_dpia_sample.html"
with open(out_path, "w") as f:
    f.write(html)
print(f"  Saved → {out_path}")


# ── Test 3: RBI FREE ──────────────────────────────────────────────────────────
sep("Test 3: RBI FREE self-assessment")

rbi = generate_rbi_free(
    organisation="Meridian Financial Services Pvt Ltd",
    prepared_by="Priya Sharma, Chief Privacy Officer",
    period_start="2026-04-01",
    period_end="2026-06-30",
    generated_at="2026-06-16T08:00:00Z",
    run_ids=[run_id1, run_id2],
    manual_overrides={"G1": "compliant", "G2": "compliant"},
)

rsummary = rbi.summary
print(f"  Report ID         : {rbi.meta['report_id']}")
print(f"  Overall score     : {rsummary['overall_score_pct']}%")
print(f"  Pillar scores:")
for pillar, score in rsummary["pillar_scores"].items():
    bar = "█" * (score // 5) + "░" * (20 - score // 5)
    print(f"    {pillar:30} {bar} {score}%")
print(f"  Compliant         : {rsummary['compliant']}/26")
print(f"  Gaps              : {rsummary['non_compliant']}/26")

assert rbi.meta["report_id"].startswith("RBI-FREE-")
assert 0 < rsummary["overall_score_pct"] <= 100
assert len(rbi.sections) == 5
assert rsummary["compliant"] > 0
print("  PASS — RBI FREE report generated correctly")


# ── Test 4: RBI FREE → HTML ───────────────────────────────────────────────────
sep("Test 4: RBI FREE → HTML rendering")
rbi_dict = json.loads(rbi.to_json())
rbi_dict["_type"] = "rbi_free"
rbi_html = render_rbi_free(rbi_dict)

assert "RBI FREE" in rbi_html
assert "Meridian Financial Services" in rbi_html
assert str(rsummary["overall_score_pct"]) + "%" in rbi_html
print(f"  HTML length : {len(rbi_html):,} chars")
print("  PASS")

rbi_out = "/tmp/svitch_rbi_free_sample.html"
with open(rbi_out, "w") as f:
    f.write(rbi_html)
print(f"  Saved → {rbi_out}")


# ── Test 5: Top gaps surface correctly ────────────────────────────────────────
sep("Test 5: Gap identification")
top_gaps = rsummary.get("top_gaps", [])
print(f"  Top gaps identified: {len(top_gaps)}")
for g in top_gaps:
    print(f"    {g[:80]}")
assert len(top_gaps) > 0
print("  PASS — gaps surface correctly")


print(f"\n{'═'*54}")
print(f"  ALL COMPLIANCE ENGINE TESTS PASSED")
print(f"{'═'*54}")
print(f"\n  Preview reports:")
print(f"    open {out_path}")
print(f"    open {rbi_out}\n")
