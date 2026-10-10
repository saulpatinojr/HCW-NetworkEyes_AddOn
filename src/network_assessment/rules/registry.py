"""The rule registry: `@rule` registers typed evaluators; `evaluate()` runs them over a topology.

Lab-edition code (not ported). Ported semantics kept from the Core's AnalysisEngine._emit (analysis_engine.py lines
165-199 at 5d3b914): every finding passes the observed-state enforcer, carries at least one framework mapping, and is
deduplicated on `rule_id:resource_id` (the first occurrence wins). Rules that need live reads are registered with
`applies_to="live-only"` and surface in `unknowns[]` rather than being dropped silently.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Literal

from network_assessment.model.enforcer import ObservedStateEnforcer
from network_assessment.model.findings import Finding, FindingSeverity, FrameworkMapping, ObservedState, Unknown
from network_assessment.model.topology import AzureSubscriptionTopology, AzureTopology
from network_assessment.rules.taxonomy import classify_traffic_direction

RULES_VERSION = "2026.10.0"

AppliesTo = Literal["export", "live-only"]
NO_PROPERTIES_REASON = "the export has no properties column, so the fields this rule reads are absent"


@dataclass(frozen=True)
class Emit:
    """One observation yielded by a rule function; the registry turns it into a Finding."""

    resource_id: str
    resource_type: str
    fact: str
    evidence_ref: str
    region: str | None = None
    title: str | None = None
    description: str | None = None
    affected_resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class NotEvaluable:
    """Yielded by a rule that cannot decide over this export (becomes one `unknowns[]` entry per rule)."""

    reason: str


Evaluator = Callable[[AzureSubscriptionTopology, AzureTopology], Iterable[Emit | NotEvaluable]]


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: FindingSeverity
    category: str
    version: int
    learn_url: str
    frameworks: tuple[FrameworkMapping, ...]
    applies_to: AppliesTo
    evidence: str
    remediation: str
    description: str
    needs_properties: bool = True
    func: Evaluator | None = field(default=None, compare=False, repr=False)


RULES: dict[str, Rule] = {}


def _register(r: Rule) -> Rule:
    if r.id in RULES:
        raise ValueError(f"duplicate rule id {r.id}")
    if r.applies_to == "export" and r.func is None:
        raise ValueError(f"{r.id}: an export rule needs an evaluator")
    if not r.frameworks:
        raise ValueError(f"{r.id}: every rule maps to at least one framework control")
    RULES[r.id] = r
    return r


def rule(
    *,
    id: str,
    title: str,
    severity: FindingSeverity,
    category: str,
    version: int,
    learn_url: str,
    frameworks: tuple[FrameworkMapping, ...],
    evidence: str,
    remediation: str,
    description: str,
    applies_to: AppliesTo = "export",
    needs_properties: bool = True,
) -> Callable[[Evaluator], Evaluator]:
    def decorator(func: Evaluator) -> Evaluator:
        _register(
            Rule(
                id=id,
                title=title,
                severity=severity,
                category=category,
                version=version,
                learn_url=learn_url,
                frameworks=tuple(frameworks),
                applies_to=applies_to,
                evidence=evidence,
                remediation=remediation,
                description=description,
                needs_properties=needs_properties,
                func=func,
            )
        )
        return func

    return decorator


def live_only(
    *,
    id: str,
    title: str,
    severity: FindingSeverity,
    category: str,
    version: int,
    learn_url: str,
    frameworks: tuple[FrameworkMapping, ...],
    evidence: str,
    remediation: str,
    description: str,
) -> Rule:
    """Register a rule the lab cannot evaluate (metrics, diagnostic settings, cost); it surfaces in unknowns[]."""
    return _register(
        Rule(
            id=id,
            title=title,
            severity=severity,
            category=category,
            version=version,
            learn_url=learn_url,
            frameworks=tuple(frameworks),
            applies_to="live-only",
            evidence=evidence,
            remediation=remediation,
            description=description,
            needs_properties=False,
            func=None,
        )
    )


@dataclass
class EvaluationResult:
    findings: list[Finding]
    unknowns: list[Unknown]


def iter_rules() -> Iterator[Rule]:
    yield from (RULES[k] for k in sorted(RULES))


def evaluate(topology: AzureTopology) -> EvaluationResult:
    """Run every registered rule over every subscription; dedup `rule_id:resource_id`; enforce observed facts."""
    enforcer = ObservedStateEnforcer()
    seen: set[str] = set()
    findings: list[Finding] = []
    unknowns: dict[str, Unknown] = {}
    for r in iter_rules():
        if r.applies_to == "live-only" or r.func is None:
            unknowns[r.id] = Unknown(rule_id=r.id, reason=f"needs a live read: {r.evidence}")
            continue
        if r.needs_properties and not topology.has_properties:
            unknowns[r.id] = Unknown(rule_id=r.id, reason=NO_PROPERTIES_REASON)
            continue
        for sub in topology.subscriptions:
            for item in r.func(sub, topology):
                if isinstance(item, NotEvaluable):
                    unknowns.setdefault(r.id, Unknown(rule_id=r.id, reason=item.reason))
                    continue
                key = f"{r.id}:{item.resource_id}"
                if key in seen:
                    continue
                seen.add(key)
                finding = Finding(
                    id=key,
                    rule_id=r.id,
                    rule_version=r.version,
                    severity=r.severity,
                    platform="azure",
                    region=item.region or "Global",
                    category=r.category,
                    title=item.title or r.title,
                    description=item.description or r.description,
                    resource_id=item.resource_id,
                    resource_type=item.resource_type,
                    account_id=sub.subscription_id,
                    observed_state=ObservedState(state="observed", fact=item.fact, evidence_ref=item.evidence_ref),
                    affected_resources=list(item.affected_resources),
                    framework_mappings=list(r.frameworks),
                    remediation=r.remediation,
                    learn_url=r.learn_url,
                    traffic_direction=classify_traffic_direction(r.id, r.category, item.resource_type),
                )
                enforcer.validate(finding)
                findings.append(finding)
    return EvaluationResult(findings=findings, unknowns=[unknowns[k] for k in sorted(unknowns)])


def rules_table() -> list[dict]:
    """The registry serialised for GET /api/rules, docs/rules/catalog.md and rules.json in the bundle."""
    return [
        {
            "id": r.id,
            "title": r.title,
            "severity": r.severity.value,
            "category": r.category,
            "version": r.version,
            "appliesTo": r.applies_to,
            "evidence": r.evidence,
            "needsProperties": r.needs_properties,
            "description": r.description,
            "remediation": r.remediation,
            "learnUrl": r.learn_url,
            "frameworks": [m.model_dump(by_alias=True, exclude_none=True) for m in r.frameworks],
        }
        for r in iter_rules()
    ]
