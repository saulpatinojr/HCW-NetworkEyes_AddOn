"""Build an Assessment from parsed rows: normalise, classify, evaluate, summarise. The one entry point the API calls."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from network_assessment.engine import (
    RULES_VERSION,
    TOPOLOGY_MODEL_VERSION,
    Finding,
    classify_topology,
    evaluate,
    rule_count,
    topology_document,
)
from network_assessment.report.summary import SEVERITIES, Assessment, ResourceView, Summary, TopologySummary


def _resource_views(normalized: Any, findings: list[Finding]) -> list[ResourceView]:
    """One view per network row; a finding belongs to the row whose id is the longest prefix of its resource id."""
    rows = [r for r in normalized.rows if r.type.startswith("microsoft.network/")]
    by_prefix = sorted(((r.id.lower(), r.id) for r in rows), key=lambda x: -len(x[0]))
    owner: dict[str, list[str]] = {}
    for f in findings:
        rid = (f.resource_id or "").lower()
        for low, original in by_prefix:
            if rid == low or rid.startswith(low + "/"):
                owner.setdefault(original, []).append(f.id or "")
                break
    return [
        ResourceView(
            id=r.id,
            name=r.name,
            type=r.type,
            location=r.location,
            subscription_id=r.subscription_id,
            resource_group=r.resource_group,
            finding_ids=owner.get(r.id, []),
            facts=normalized.facts.get(r.id, {}),
        )
        for r in rows
    ]


def assess(
    normalized: Any,
    *,
    source_format: str,
    file_name: str | None = None,
    row_count: int,
    assessment_id: str | None = None,
    now: datetime | None = None,
) -> tuple[Assessment, dict[str, Any]]:
    """Evaluate a normalised export. Returns the assessment and the topology document (for topology.json)."""
    topology = normalized.topology
    result = evaluate(topology)
    classification = classify_topology(topology)
    by_severity = Counter(f.severity.value for f in result.findings)
    summary = Summary(
        resource_count=sum(n for t, n in topology.resource_counts.items() if t.startswith("microsoft.network/")),
        row_count=row_count,
        subscriptions=[s.subscription_id for s in topology.subscriptions],
        by_type=dict(topology.resource_counts),
        topology=TopologySummary.from_classification(classification),
        findings_count=len(result.findings),
        findings_by_severity={sev: by_severity.get(sev, 0) for sev in SEVERITIES},
        unknown_rules=len(result.unknowns),
        rules_evaluated=rule_count() - len(result.unknowns),
        warnings=list(topology.warnings),
        rules_version=RULES_VERSION,
        model_version=TOPOLOGY_MODEL_VERSION,
        generated_at=now or datetime.now(UTC),
    )
    assessment = Assessment(
        id=assessment_id or str(uuid.uuid4()),
        created_at=summary.generated_at,
        source_format=source_format,
        file_name=file_name,
        rules_version=RULES_VERSION,
        model_version=TOPOLOGY_MODEL_VERSION,
        summary=summary,
        findings=result.findings,
        resources=_resource_views(normalized, result.findings),
        unknowns=result.unknowns,
        warnings=list(topology.warnings),
    )
    return assessment, topology_document(topology)
