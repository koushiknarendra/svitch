"""
Svitch Consent Ledger API

POST /consent/grant          — Record a new consent grant
POST /consent/{id}/withdraw  — Withdraw consent
GET  /consent/{id}/verify    — Verify consent is active (for agents before processing)
GET  /consent/{id}/proof     — Generate portable cryptographic proof
GET  /consent/principal/{id} — List all consents for a data principal
GET  /chain/verify           — Verify the entire consent chain is intact
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SVITCH_CONSENT_DB", os.path.join(ROOT, "svitch_consent.db"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

import ledger as L

app = FastAPI(
    title="Svitch Consent Ledger",
    description="DPDP-compliant consent records — cryptographically verifiable, independently auditable.",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

L.init_db()


class GrantRequest(BaseModel):
    data_principal_id: str
    purpose: str
    data_categories: list[str]
    legal_basis: str = "explicit_consent"
    expires_at_ms: Optional[int] = None
    version: str = "1.0"
    channel: str = "web"
    ip_address: str = ""
    agent_id: Optional[str] = None


@app.get("/health")
def health():
    valid, msg, count = L.verify_chain()
    return {"status": "ok", "version": "0.1.0", "chain_valid": valid, "records": count}


@app.post("/consent/grant")
def grant_consent(req: GrantRequest):
    record = L.grant(
        data_principal_id=req.data_principal_id,
        purpose=req.purpose,
        data_categories=req.data_categories,
        legal_basis=req.legal_basis,
        expires_at_ms=req.expires_at_ms,
        version=req.version,
        channel=req.channel,
        ip_address=req.ip_address,
        agent_id=req.agent_id,
    )
    return {
        "consent_id": record.consent_id,
        "status": record.status,
        "record_hash": record.record_hash,
        "granted_at_ms": record.granted_at_ms,
        "fabric_tx_id": record.fabric_tx_id,
        "message": "Consent recorded. Store the consent_id to reference this record.",
    }


@app.post("/consent/{consent_id}/withdraw")
def withdraw_consent(consent_id: str):
    try:
        record = L.withdraw(consent_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {
        "consent_id": consent_id,
        "withdrawal_id": record.consent_id,
        "status": "withdrawn",
        "withdrawn_at_ms": record.withdrawn_at_ms,
        "record_hash": record.record_hash,
        "message": "Withdrawal recorded on the ledger. Original grant record is preserved.",
    }


@app.get("/consent/{consent_id}/verify")
def verify_consent(consent_id: str):
    valid, reason, record = L.verify(consent_id)
    return {
        "consent_id": consent_id,
        "valid": valid,
        "reason": reason,
        "purpose": record.purpose if record else None,
        "data_categories": record.data_categories if record else None,
        "status": record.status if record else None,
    }


@app.get("/consent/{consent_id}/proof")
def get_proof(consent_id: str):
    try:
        return L.proof(consent_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/consent/principal/{data_principal_id}")
def get_principal_consents(data_principal_id: str, active_only: bool = False):
    records = (
        L.get_active_consents(data_principal_id)
        if active_only else
        L.get_consents(data_principal_id)
    )
    return {
        "count": len(records),
        "consents": [
            {
                "consent_id": r.consent_id,
                "purpose": r.purpose,
                "data_categories": r.data_categories,
                "status": r.status,
                "granted_at_ms": r.granted_at_ms,
                "withdrawn_at_ms": r.withdrawn_at_ms,
                "record_hash": r.record_hash,
            }
            for r in records
        ],
    }


@app.get("/chain/verify")
def verify_chain():
    valid, msg, count = L.verify_chain()
    return {"valid": valid, "message": msg, "records_checked": count}
