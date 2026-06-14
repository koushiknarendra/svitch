"""
Append-only, hash-chained audit log.

Each record includes the SHA-256 hash of the previous record —
forming a Merkle chain. Tampering with any record breaks the chain,
making the log tamper-evident without requiring a blockchain.

Storage backends:
  - SQLite  (default, zero config, local dev + single-server)
  - Postgres/Supabase (production, set DATABASE_URL env var)
"""

import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class AuditRecord:
    id: str
    run_id: str
    agent_id: str
    event_type: str        # llm_call | tool_call | decision | human_checkpoint | pii_detected
    timestamp_ms: int
    data: dict             # event-specific payload
    pii_types: list[str]   # PII entity types detected in this event
    pii_redacted: bool
    human_approved: Optional[bool]
    prev_hash: str
    record_hash: str       # SHA-256 of this record's canonical fields


def _hash_record(record: AuditRecord) -> str:
    canonical = {
        "id": record.id,
        "run_id": record.run_id,
        "agent_id": record.agent_id,
        "event_type": record.event_type,
        "timestamp_ms": record.timestamp_ms,
        "data": record.data,
        "pii_types": record.pii_types,
        "prev_hash": record.prev_hash,
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


_DB_PATH = os.environ.get("SVITCH_DB_PATH", "svitch_audit.db")
_DATABASE_URL = os.environ.get("DATABASE_URL")

# Singleton connection for :memory: — required because each sqlite3.connect(":memory:")
# creates a fresh, isolated database. All callers must share one connection.
_memory_conn: Optional[sqlite3.Connection] = None


def _get_sqlite_conn() -> sqlite3.Connection:
    global _memory_conn
    if _DB_PATH == ":memory:":
        if _memory_conn is None:
            _memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            _memory_conn.row_factory = sqlite3.Row
        return _memory_conn
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    if _DATABASE_URL:
        _init_postgres()
    else:
        _init_sqlite()


def _init_sqlite():
    conn = _get_sqlite_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp_ms INTEGER NOT NULL,
            data TEXT NOT NULL,
            pii_types TEXT NOT NULL,
            pii_redacted INTEGER NOT NULL,
            human_approved INTEGER,
            prev_hash TEXT NOT NULL,
            record_hash TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON audit_log(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON audit_log(agent_id)")
    conn.commit()


def _init_postgres():
    try:
        import psycopg2
        conn = psycopg2.connect(_DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp_ms BIGINT NOT NULL,
                data JSONB NOT NULL,
                pii_types JSONB NOT NULL,
                pii_redacted BOOLEAN NOT NULL,
                human_approved BOOLEAN,
                prev_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL UNIQUE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON audit_log(run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON audit_log(agent_id)")
        conn.commit()
        conn.close()
    except ImportError:
        raise RuntimeError("Install psycopg2: pip install psycopg2-binary")


def _get_last_hash(run_id: str) -> str:
    """Get the hash of the last record in a run, or genesis hash if first."""
    if _DATABASE_URL:
        return _get_last_hash_postgres(run_id)

    conn = _get_sqlite_conn()
    # rowid = insertion order — safe tiebreaker when timestamp_ms values collide
    row = conn.execute(
        "SELECT record_hash FROM audit_log WHERE run_id = ? ORDER BY rowid DESC LIMIT 1",
        (run_id,)
    ).fetchone()
    return row["record_hash"] if row else "0" * 64


def _get_last_hash_postgres(run_id: str) -> str:
    import psycopg2
    conn = psycopg2.connect(_DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT record_hash FROM audit_log WHERE run_id = %s ORDER BY timestamp_ms DESC LIMIT 1",
        (run_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "0" * 64


def append(
    run_id: str,
    agent_id: str,
    event_type: str,
    data: dict,
    pii_types: list[str] = None,
    pii_redacted: bool = False,
    human_approved: Optional[bool] = None,
) -> AuditRecord:
    """Append an event to the audit log. Returns the created record."""
    prev_hash = _get_last_hash(run_id)

    record = AuditRecord(
        id=str(uuid.uuid4()),
        run_id=run_id,
        agent_id=agent_id,
        event_type=event_type,
        timestamp_ms=int(time.time() * 1000),
        data=data,
        pii_types=pii_types or [],
        pii_redacted=pii_redacted,
        human_approved=human_approved,
        prev_hash=prev_hash,
        record_hash="",
    )
    record.record_hash = _hash_record(record)

    _write_record(record)
    return record


def _write_record(record: AuditRecord):
    if _DATABASE_URL:
        _write_record_postgres(record)
        return

    conn = _get_sqlite_conn()
    conn.execute("""
        INSERT INTO audit_log VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record.id,
        record.run_id,
        record.agent_id,
        record.event_type,
        record.timestamp_ms,
        json.dumps(record.data),
        json.dumps(record.pii_types),
        int(record.pii_redacted),
        None if record.human_approved is None else int(record.human_approved),
        record.prev_hash,
        record.record_hash,
    ))
    conn.commit()


def _write_record_postgres(record: AuditRecord):
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(_DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_log VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        record.id, record.run_id, record.agent_id, record.event_type,
        record.timestamp_ms,
        psycopg2.extras.Json(record.data),
        psycopg2.extras.Json(record.pii_types),
        record.pii_redacted,
        record.human_approved,
        record.prev_hash,
        record.record_hash,
    ))
    conn.commit()
    conn.close()


def get_run(run_id: str) -> list[AuditRecord]:
    """Retrieve all events for a run, in order."""
    if _DATABASE_URL:
        return _get_run_postgres(run_id)

    conn = _get_sqlite_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE run_id = ? ORDER BY rowid ASC",
        (run_id,)
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def _get_run_postgres(run_id: str) -> list[AuditRecord]:
    import psycopg2
    conn = psycopg2.connect(_DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM audit_log WHERE run_id = %s ORDER BY timestamp_ms ASC",
        (run_id,)
    )
    rows = cur.fetchall()
    conn.close()
    cols = ["id","run_id","agent_id","event_type","timestamp_ms","data",
            "pii_types","pii_redacted","human_approved","prev_hash","record_hash"]
    return [_row_to_record(dict(zip(cols, r))) for r in rows]


def _row_to_record(row) -> AuditRecord:
    if isinstance(row, sqlite3.Row):
        row = dict(row)
    data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
    pii_types = row["pii_types"] if isinstance(row["pii_types"], list) else json.loads(row["pii_types"])
    return AuditRecord(
        id=row["id"],
        run_id=row["run_id"],
        agent_id=row["agent_id"],
        event_type=row["event_type"],
        timestamp_ms=row["timestamp_ms"],
        data=data,
        pii_types=pii_types,
        pii_redacted=bool(row["pii_redacted"]),
        human_approved=None if row["human_approved"] is None else bool(row["human_approved"]),
        prev_hash=row["prev_hash"],
        record_hash=row["record_hash"],
    )


def verify_chain(run_id: str) -> tuple[bool, Optional[str]]:
    """
    Verify the hash chain for a run.
    Returns (is_valid, error_message).
    A valid chain proves no records have been tampered with.
    """
    records = get_run(run_id)
    if not records:
        return True, None

    expected_prev = "0" * 64
    for record in records:
        if record.prev_hash != expected_prev:
            return False, f"Chain broken at record {record.id}: prev_hash mismatch"
        recomputed = _hash_record(record)
        if recomputed != record.record_hash:
            return False, f"Record {record.id} has been tampered with"
        expected_prev = record.record_hash

    return True, None
