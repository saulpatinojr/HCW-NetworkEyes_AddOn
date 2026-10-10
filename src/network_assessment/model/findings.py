# Ported from saulpatinojr/HCW-NetworkEyes_App cna/core/findings_schema.py at 5d3b914; changes: MCP and review
# fields
# dropped (recommendations[].source, recommendation_source, human_reviewed, human_notes, est_monthly_cost_usd,
# data_confidence, status, FindingRecommendation, FindingStatus); ObservedState gained `state`; Finding gained
# `rule_version`, `remediation`, `learn_url`; `account_id` serialises as `subscriptionId`; camelCase aliases on output;
# FindingsReport replaced by the lab's Assessment document (report/summary.py); `Unknown` added (REFACTOR_APP.md 9).
"""Universal findings schema.

DD-002: observed_state is REQUIRED — only what was discovered, no assumptions.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

FINDINGS_MODEL_VERSION = "lab-1.0.0"

EvidenceState = Literal["observed", "unknown", "not-applicable"]


class FindingSeverity(enum.StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ObservedState(_Camel):
    state: EvidenceState = "observed"
    fact: str
    evidence_ref: str


class FrameworkMapping(_Camel):
    framework: str  # e.g. "CIS Microsoft Azure Foundations Benchmark"
    version: str | None = None
    pillar: str | None = None
    control: str | None = None
    control_id: str | None = None
    control_name: str | None = None
    alignment: str | None = None


class Finding(_Camel):
    id: str | None = None
    rule_id: str | None = None
    rule_version: int = 1
    severity: FindingSeverity  # critical | high | medium | low | informational
    platform: str | None = "azure"
    region: str | None = None
    category: str | None = None
    title: str
    description: str | None = None
    resource_id: str | None = None
    resource_type: str | None = None
    account_id: str | None = Field(default=None, alias="subscriptionId")
    observed_state: ObservedState  # DD-002: ONLY what was discovered — no assumptions

    @field_validator("observed_state", mode="before")
    @classmethod
    def _coerce_observed_state(cls, v: Any) -> Any:
        """Accept a plain string for observed_state by wrapping it in ObservedState."""
        if isinstance(v, str):
            return ObservedState(fact=v, evidence_ref="")
        return v

    affected_resources: list[str] = Field(default_factory=list)
    framework_mappings: list[FrameworkMapping] = Field(default_factory=list)
    remediation: str | None = None
    learn_url: str | None = None
    # Traffic plane: "east_west" | "north_south" | "management" | "" (unclassified).
    # Populated by network_assessment.rules.taxonomy.classify_traffic_direction.
    traffic_direction: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = FINDINGS_MODEL_VERSION


class Unknown(_Camel):
    """A rule that could not be evaluated over this input, and why (REFACTOR_APP.md section 9)."""

    rule_id: str
    reason: str
