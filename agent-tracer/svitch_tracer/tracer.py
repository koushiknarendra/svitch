"""
SvitchTracer — the main interface developers use.

Usage:
    from svitch_tracer import SvitchTracer

    tracer = SvitchTracer(agent_id="loan-processor-v1")

    with tracer.run() as run:
        run.llm_call(
            provider="openai",
            model="gpt-4o",
            prompt="Summarise loan application for Rahul...",
            response="Applicant has good credit history...",
        )
        run.tool_call(tool="fetch_cibil_score", input={"pan": "ABCDE1234F"}, output={"score": 780})
        run.decision(reason="CIBIL above threshold", outcome="approve", confidence=0.94)
"""

import sys
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

# Import PII detection from the sibling pii-shield module if available
_PII_SHIELD_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pii-shield", "service")
if os.path.isdir(_PII_SHIELD_PATH):
    sys.path.insert(0, _PII_SHIELD_PATH)

try:
    from detectors import detect_all, redact_all
    _PII_AVAILABLE = True
except ImportError:
    _PII_AVAILABLE = False

from .storage import db


@dataclass
class RunContext:
    run_id: str
    agent_id: str
    _tracer: "SvitchTracer"

    def llm_call(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        redact_pii: bool = True,
        metadata: dict = None,
    ) -> db.AuditRecord:
        """Record an LLM API call. PII is detected in both prompt and response."""
        pii_types = []
        if _PII_AVAILABLE:
            prompt_entities = detect_all(prompt)
            response_entities = detect_all(response)
            pii_types = list({e.type for e in prompt_entities + response_entities})
            if redact_pii and pii_types:
                prompt, _ = redact_all(prompt)
                response, _ = redact_all(response)

        return db.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="llm_call",
            data={
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "response": response,
                **(metadata or {}),
            },
            pii_types=pii_types,
            pii_redacted=redact_pii and bool(pii_types),
        )

    def tool_call(
        self,
        tool: str,
        input: dict,
        output: dict,
        redact_pii: bool = True,
        metadata: dict = None,
    ) -> db.AuditRecord:
        """Record a tool/function call made by the agent."""
        pii_types = []
        input_str = str(input)
        output_str = str(output)

        if _PII_AVAILABLE:
            all_entities = detect_all(input_str) + detect_all(output_str)
            pii_types = list({e.type for e in all_entities})

        return db.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="tool_call",
            data={
                "tool": tool,
                "input": input,
                "output": output,
                **(metadata or {}),
            },
            pii_types=pii_types,
            pii_redacted=False,  # Tool inputs/outputs preserved for audit; PII flagged not removed
        )

    def decision(
        self,
        reason: str,
        outcome: str,
        confidence: Optional[float] = None,
        metadata: dict = None,
    ) -> db.AuditRecord:
        """Record a decision made by the agent."""
        return db.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="decision",
            data={
                "reason": reason,
                "outcome": outcome,
                **({"confidence": confidence} if confidence is not None else {}),
                **(metadata or {}),
            },
        )

    def human_checkpoint(
        self,
        question: str,
        approved: bool,
        reviewer_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> db.AuditRecord:
        """
        Record a human-in-the-loop checkpoint.
        Required by RBI FREE Framework for high-risk AI decisions.
        """
        return db.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="human_checkpoint",
            data={
                "question": question,
                "reviewer_id": reviewer_id,
                "notes": notes,
            },
            human_approved=approved,
        )

    def data_access(
        self,
        source: str,
        fields_accessed: list[str],
        purpose: str,
        data_principal_id: Optional[str] = None,
    ) -> db.AuditRecord:
        """
        Record access to personal data.
        DPDP requires logging: what data was accessed, for what purpose, and whose.
        """
        return db.append(
            run_id=self.run_id,
            agent_id=self.agent_id,
            event_type="data_access",
            data={
                "source": source,
                "fields_accessed": fields_accessed,
                "purpose": purpose,
                **({"data_principal_id": data_principal_id} if data_principal_id else {}),
            },
        )

    def verify(self) -> tuple[bool, Optional[str]]:
        """Verify the hash chain for this run. Returns (is_valid, error_or_none)."""
        return db.verify_chain(self.run_id)

    def get_records(self) -> list[db.AuditRecord]:
        """Retrieve all records for this run."""
        return db.get_run(self.run_id)


class SvitchTracer:
    """
    Main entry point. One tracer per agent type.

    Args:
        agent_id: Unique identifier for this agent (e.g. "loan-processor-v2")
        auto_init_db: Initialize the database on creation (default True)
    """

    def __init__(self, agent_id: str, auto_init_db: bool = True):
        self.agent_id = agent_id
        if auto_init_db:
            db.init_db()

    @contextmanager
    def run(self, run_id: Optional[str] = None):
        """
        Context manager for a single agent execution run.
        Yields a RunContext for recording events.

            with tracer.run() as run:
                run.llm_call(...)
                run.decision(...)
        """
        run_id = run_id or str(uuid.uuid4())
        ctx = RunContext(run_id=run_id, agent_id=self.agent_id, _tracer=self)
        yield ctx

    def get_run(self, run_id: str) -> list[db.AuditRecord]:
        return db.get_run(run_id)

    def verify_run(self, run_id: str) -> tuple[bool, Optional[str]]:
        return db.verify_chain(run_id)
