"""
Base dataclasses shared across all report generators.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Literal
import json


ReportStatus = Literal["compliant", "partial", "non_compliant", "not_assessed"]


@dataclass
class CheckItem:
    id: str
    requirement: str
    status: ReportStatus
    evidence: str = ""
    gap: str = ""
    recommendation: str = ""


@dataclass
class RiskItem:
    id: str
    description: str
    likelihood: Literal["low", "medium", "high"]
    impact: Literal["low", "medium", "high"]
    mitigation: str
    residual_risk: Literal["low", "medium", "high"]


@dataclass
class ProcessingActivity:
    name: str
    purpose: str
    legal_basis: str
    data_categories: list[str]
    data_principals: str          # "customers", "employees", etc.
    retention_period: str
    third_party_processors: list[str]
    cross_border_transfer: bool


@dataclass
class ReportMeta:
    report_id: str
    report_type: str
    organisation: str
    prepared_by: str
    period_start: str
    period_end: str
    generated_at: str
    version: str = "1.0"


@dataclass
class BaseReport:
    meta: ReportMeta
    summary: dict = field(default_factory=dict)
    sections: list[dict] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, default=str)

    def compliance_score(self) -> float:
        """Returns 0.0–1.0 based on CheckItems across all sections."""
        total = compliant = 0
        for section in self.sections:
            for item in section.get("checks", []):
                total += 1
                if item.get("status") == "compliant":
                    compliant += 1
        return round(compliant / total, 2) if total else 0.0
