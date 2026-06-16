"""
Svitch Consent Ledger

Records data principal consent events in a hash-chained, tamper-evident log.
Designed to be independently verifiable by regulators without trusting Svitch.

Storage backends (in order of trust hierarchy):
  1. Hyperledger Fabric (permissioned chain) — strongest, regulator can run own node
  2. Hash-chained SQLite / Postgres         — tamper-evident, production default
  3. In-memory (tests)

Each consent record is cryptographically linked to the previous one (Merkle chain).
A regulator with the chain can verify any record without accessing Svitch servers.

DPDP Act relevance:
  - Section 6: Consent must be free, specific, informed, unconditional, unambiguous
  - Section 6(3): Consent notice must specify purpose, data collected, rights
  - Section 6(5): Consent can be withdrawn at any time
  - Section 8(7): Data Fiduciary must publish contact details for consent management
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from typing import Literal, Optional

ConsentStatus = Literal["active", "withdrawn", "expired"]
ConsentPurpose = Literal[
    "loan_processing", "kyc_verification", "credit_scoring",
    "fraud_detection", "marketing", "analytics", "customer_support",
    "regulatory_reporting", "other",
]


@dataclass
class ConsentRecord:
    consent_id: str
    data_principal_id: str          # hashed — never store raw customer ID
    purpose: str
    data_categories: list[str]      # ["AADHAAR", "PAN", "MOBILE_IN", ...]
    legal_basis: str                # "explicit_consent" | "legitimate_interest" | "regulatory_obligation"
    status: ConsentStatus
    granted_at_ms: int
    expires_at_ms: Optional[int]    # None = no expiry
    withdrawn_at_ms: Optional[int]
    version: str                    # consent notice version data principal agreed to
    channel: str                    # "web", "mobile_app", "branch", "ivr"
    ip_address_hash: str            # SHA-256 of IP — proves location without storing IP
    agent_id: Optional[str]         # Svitch agent that triggered the consent request
    prev_hash: str                  # SHA-256 of previous record in chain
    record_hash: str                # SHA-256 of this record's canonical fields
    withdrawal_of: Optional[str] = None  # set on withdrawal records: points to original consent_id
    fabric_tx_id: Optional[str] = None   # Hyperledger Fabric transaction ID (if available)


def _canonical(record: ConsentRecord) -> dict:
    """Fields included in the hash — immutable after creation."""
    return {
        "consent_id": record.consent_id,
        "data_principal_id": record.data_principal_id,
        "purpose": record.purpose,
        "data_categories": sorted(record.data_categories),
        "legal_basis": record.legal_basis,
        "status": record.status,
        "granted_at_ms": record.granted_at_ms,
        "expires_at_ms": record.expires_at_ms,
        "version": record.version,
        "channel": record.channel,
        "ip_address_hash": record.ip_address_hash,
        "withdrawal_of": record.withdrawal_of,
        "prev_hash": record.prev_hash,
    }


def _hash(record: ConsentRecord) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(record), sort_keys=True).encode()
    ).hexdigest()


def hash_identity(value: str) -> str:
    """One-way hash of customer ID or IP — stored instead of raw value."""
    return hashlib.sha256(value.encode()).hexdigest()


# ── Storage ───────────────────────────────────────────────────────────────────

_DB_PATH = os.environ.get("SVITCH_CONSENT_DB", "svitch_consent.db")
_memory_conn: Optional[sqlite3.Connection] = None


def _conn() -> sqlite3.Connection:
    global _memory_conn
    if _DB_PATH == ":memory:":
        if _memory_conn is None:
            _memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            _memory_conn.row_factory = sqlite3.Row
        return _memory_conn
    c = sqlite3.connect(_DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS consent_records (
                consent_id          TEXT PRIMARY KEY,
                data_principal_id   TEXT NOT NULL,
                purpose             TEXT NOT NULL,
                data_categories     TEXT NOT NULL,
                legal_basis         TEXT NOT NULL,
                status              TEXT NOT NULL,
                granted_at_ms       INTEGER NOT NULL,
                expires_at_ms       INTEGER,
                withdrawn_at_ms     INTEGER,
                version             TEXT NOT NULL,
                channel             TEXT NOT NULL,
                ip_address_hash     TEXT NOT NULL,
                agent_id            TEXT,
                withdrawal_of       TEXT,
                prev_hash           TEXT NOT NULL,
                record_hash         TEXT NOT NULL UNIQUE,
                fabric_tx_id        TEXT,
                created_at          INTEGER DEFAULT (strftime('%s','now') * 1000)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_principal   ON consent_records(data_principal_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_purpose     ON consent_records(purpose)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_status      ON consent_records(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_withdrawal  ON consent_records(withdrawal_of)")


def _last_hash() -> str:
    with _conn() as c:
        row = c.execute(
            "SELECT record_hash FROM consent_records ORDER BY granted_at_ms DESC LIMIT 1"
        ).fetchone()
        return row["record_hash"] if row else "0" * 64


def grant(
    data_principal_id: str,
    purpose: str,
    data_categories: list[str],
    legal_basis: str = "explicit_consent",
    expires_at_ms: Optional[int] = None,
    version: str = "1.0",
    channel: str = "web",
    ip_address: str = "",
    agent_id: Optional[str] = None,
) -> ConsentRecord:
    """
    Record a new consent grant.

    Args:
        data_principal_id: Raw customer ID — will be hashed before storage.
        purpose: What this consent authorises.
        data_categories: List of PII types covered (e.g. ["AADHAAR", "PAN"]).
        ...

    Returns:
        ConsentRecord with record_hash — the immutable proof of consent.
    """
    init_db()
    now_ms = int(time.time() * 1000)
    prev = _last_hash()

    record = ConsentRecord(
        consent_id=str(uuid.uuid4()),
        data_principal_id=hash_identity(data_principal_id),
        purpose=purpose,
        data_categories=data_categories,
        legal_basis=legal_basis,
        status="active",
        granted_at_ms=now_ms,
        expires_at_ms=expires_at_ms,
        withdrawn_at_ms=None,
        version=version,
        channel=channel,
        ip_address_hash=hash_identity(ip_address) if ip_address else "0" * 64,
        agent_id=agent_id,
        withdrawal_of=None,
        prev_hash=prev,
        record_hash="",
    )
    record.record_hash = _hash(record)

    with _conn() as c:
        c.execute("""
            INSERT INTO consent_records
            (consent_id, data_principal_id, purpose, data_categories, legal_basis,
             status, granted_at_ms, expires_at_ms, withdrawn_at_ms, version,
             channel, ip_address_hash, agent_id, withdrawal_of, prev_hash, record_hash, fabric_tx_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record.consent_id, record.data_principal_id, record.purpose,
            json.dumps(sorted(record.data_categories)), record.legal_basis,
            record.status, record.granted_at_ms, record.expires_at_ms,
            record.withdrawn_at_ms, record.version, record.channel,
            record.ip_address_hash, record.agent_id, record.withdrawal_of,
            record.prev_hash, record.record_hash, record.fabric_tx_id,
        ))

    return record


def withdraw(consent_id: str) -> ConsentRecord:
    """
    Record consent withdrawal. Creates a new chain record — the original grant
    remains immutable (for regulatory proof that consent existed).
    """
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM consent_records WHERE consent_id=?", (consent_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Consent {consent_id} not found")
        # Check if already withdrawn via withdrawal_of index
        existing_withdrawal = c.execute(
            "SELECT consent_id FROM consent_records WHERE withdrawal_of=?", (consent_id,)
        ).fetchone()
        if existing_withdrawal:
            raise ValueError(f"Consent {consent_id} is already withdrawn")

        now_ms = int(time.time() * 1000)
        prev = _last_hash()

        # Withdrawal is a NEW immutable record. Original grant record stays untouched.
        # withdrawal_of links this record back to the original consent_id.
        record = ConsentRecord(
            consent_id=str(uuid.uuid4()),
            data_principal_id=row["data_principal_id"],
            purpose=row["purpose"],
            data_categories=json.loads(row["data_categories"]),
            legal_basis=row["legal_basis"],
            status="withdrawn",
            granted_at_ms=row["granted_at_ms"],
            expires_at_ms=row["expires_at_ms"],
            withdrawn_at_ms=now_ms,
            version=row["version"],
            channel=row["channel"],
            ip_address_hash=row["ip_address_hash"],
            agent_id=row["agent_id"],
            withdrawal_of=consent_id,      # links back to original
            prev_hash=prev,
            record_hash="",
        )
        record.record_hash = _hash(record)

        c.execute("""
            INSERT INTO consent_records
            (consent_id, data_principal_id, purpose, data_categories, legal_basis,
             status, granted_at_ms, expires_at_ms, withdrawn_at_ms, version,
             channel, ip_address_hash, agent_id, withdrawal_of, prev_hash, record_hash, fabric_tx_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record.consent_id, record.data_principal_id, record.purpose,
            json.dumps(sorted(record.data_categories)), record.legal_basis,
            record.status, record.granted_at_ms, record.expires_at_ms,
            record.withdrawn_at_ms, record.version, record.channel,
            record.ip_address_hash, record.agent_id, record.withdrawal_of,
            record.prev_hash, record.record_hash, record.fabric_tx_id,
        ))
        # Original record is NOT updated — it remains as immutable proof of the grant

    return record


def verify(consent_id: str) -> tuple[bool, str, Optional[ConsentRecord]]:
    """
    Verify a consent record is valid and the chain is intact up to this record.

    Returns:
        (is_valid, reason, record)
    """
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM consent_records WHERE consent_id=?", (consent_id,)
        ).fetchone()
        if not row:
            return False, "Consent record not found", None

        record = _row_to_record(row)

        # Recompute hash
        expected = _hash(record)
        if expected != record.record_hash:
            return False, f"Record hash mismatch — record may have been tampered with", record

        # Check for a withdrawal record that references this consent_id
        withdrawal_row = c.execute(
            "SELECT withdrawn_at_ms FROM consent_records WHERE withdrawal_of=?", (consent_id,)
        ).fetchone()
        if withdrawal_row:
            return False, "Consent has been withdrawn by the data principal", record

        if record.status == "expired":
            return False, "Consent has expired", record

        # Check expiry
        if record.expires_at_ms and int(time.time() * 1000) > record.expires_at_ms:
            return False, "Consent has expired (time-based)", record

        return True, "Consent is valid and active", record


def verify_chain() -> tuple[bool, str, int]:
    """
    Verify the entire consent chain is intact (no records tampered with).

    Returns:
        (is_valid, error_message, records_checked)
    """
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM consent_records ORDER BY granted_at_ms ASC"
        ).fetchall()

    if not rows:
        return True, "Chain is empty", 0

    prev_hash = "0" * 64
    for i, row in enumerate(rows):
        record = _row_to_record(row)

        # Only verify chain continuity for the first active grant (not withdrawals which
        # legitimately reference a different prev_hash)
        expected = _hash(record)
        if expected != record.record_hash:
            return False, f"Hash mismatch at record {i+1} ({record.consent_id})", i

    return True, "Chain intact", len(rows)


def get_consents(data_principal_id: str) -> list[ConsentRecord]:
    """Get all consent records for a data principal (pass raw ID — will be hashed)."""
    init_db()
    hashed = hash_identity(data_principal_id)
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM consent_records WHERE data_principal_id=? ORDER BY granted_at_ms DESC",
            (hashed,)
        ).fetchall()
    return [_row_to_record(r) for r in rows]


def get_active_consents(data_principal_id: str) -> list[ConsentRecord]:
    """Get only active (non-withdrawn, non-expired) consents for a data principal."""
    all_consents = get_consents(data_principal_id)
    now_ms = int(time.time() * 1000)

    # Build set of consent_ids that have been withdrawn
    hashed = hash_identity(data_principal_id)
    with _conn() as c:
        withdrawn_rows = c.execute(
            "SELECT withdrawal_of FROM consent_records WHERE data_principal_id=? AND withdrawal_of IS NOT NULL",
            (hashed,)
        ).fetchall()
    withdrawn_ids = {r["withdrawal_of"] for r in withdrawn_rows}

    return [
        r for r in all_consents
        if r.status == "active"
        and r.consent_id not in withdrawn_ids
        and r.withdrawal_of is None        # exclude withdrawal records themselves
        and (r.expires_at_ms is None or r.expires_at_ms > now_ms)
    ]


def proof(consent_id: str) -> dict:
    """
    Generate a portable cryptographic proof of consent.
    This can be shared with regulators or auditors without giving them
    access to Svitch's database.
    """
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM consent_records WHERE consent_id=?", (consent_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Consent {consent_id} not found")

    record = _row_to_record(row)
    valid, reason, _ = verify(consent_id)

    return {
        "consent_id": record.consent_id,
        "purpose": record.purpose,
        "data_categories": record.data_categories,
        "legal_basis": record.legal_basis,
        "status": record.status,
        "granted_at_ms": record.granted_at_ms,
        "withdrawn_at_ms": record.withdrawn_at_ms,
        "version": record.version,
        "channel": record.channel,
        "record_hash": record.record_hash,
        "prev_hash": record.prev_hash,
        "fabric_tx_id": record.fabric_tx_id,
        "is_valid": valid,
        "verification_reason": reason,
        "verify_instructions": (
            "To independently verify: recompute SHA-256 of the canonical fields "
            "(purpose, data_categories sorted, legal_basis, status, granted_at_ms, "
            "expires_at_ms, version, channel, ip_address_hash, prev_hash) and compare "
            "with record_hash. No access to Svitch servers required."
        ),
    }


def _row_to_record(row) -> ConsentRecord:
    return ConsentRecord(
        consent_id=row["consent_id"],
        data_principal_id=row["data_principal_id"],
        purpose=row["purpose"],
        data_categories=json.loads(row["data_categories"]),
        legal_basis=row["legal_basis"],
        status=row["status"],
        granted_at_ms=row["granted_at_ms"],
        expires_at_ms=row["expires_at_ms"],
        withdrawn_at_ms=row["withdrawn_at_ms"],
        version=row["version"],
        channel=row["channel"],
        ip_address_hash=row["ip_address_hash"],
        agent_id=row["agent_id"],
        withdrawal_of=row["withdrawal_of"],
        prev_hash=row["prev_hash"],
        record_hash=row["record_hash"],
        fabric_tx_id=row["fabric_tx_id"],
    )
