"""The assessment document (design B.6): summary, findings, resources, unknowns, warnings, versions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from network_assessment.classify.topology import TopologyClassification
from network_assessment.model.findings import Finding, Unknown

SEVERITIES = ("critical", "high", "medium", "low", "informational")


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TopologySummary(_Camel):
    pattern: str
    hub_vnet_ids: list[str] = Field(default_factory=list)
    spoke_vnet_ids: list[str] = Field(default_factory=list)
    rationale: str = ""

    @classmethod
    def from_classification(cls, c: TopologyClassification) -> TopologySummary:
        return cls(
            pattern=c.pattern, hub_vnet_ids=c.hub_vnet_ids, spoke_vnet_ids=c.spoke_vnet_ids, rationale=c.rationale
        )


class Summary(_Camel):
    resource_count: int
    row_count: int
    subscriptions: list[str]
    by_type: dict[str, int]
    topology: TopologySummary
    findings_count: int
    findings_by_severity: dict[str, int]
    unknown_rules: int
    rules_evaluated: int
    warnings: list[str]
    rules_version: str
    model_version: str
    generated_at: datetime


class ResourceView(_Camel):
    """Per-resource detail for the pane's drawer: identity, the findings that name it, and the facts the rules read."""

    id: str
    name: str
    type: str
    location: str | None = None
    subscription_id: str | None = None
    resource_group: str | None = None
    finding_ids: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)


class Assessment(_Camel):
    id: str
    created_at: datetime
    source_format: str
    file_name: str | None = None
    rules_version: str
    model_version: str
    summary: Summary
    findings: list[Finding]
    resources: list[ResourceView]
    unknowns: list[Unknown]
    warnings: list[str]

    def document(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)
