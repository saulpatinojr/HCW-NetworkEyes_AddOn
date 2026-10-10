"""The sample export's results are pinned: every portable rule fires at least once (design D.6)."""

from collections import Counter

import pytest

from network_assessment.assess import assess
from network_assessment.ingestion import normalize, parse_json
from network_assessment.rules import RULES

from ..conftest import SAMPLE_JSON, SUB_HUB, SUB_SPOKE

EXPECTED_COUNTS = {
    "AZ-BCDR-001": 1,
    "AZ-BCDR-002": 1,
    "AZ-BCDR-003": 1,
    "AZ-BCDR-004": 1,
    "AZ-BCDR-005": 1,
    "AZ-BCDR-006": 2,
    "AZ-BCDR-007": 1,
    "AZ-COST-001": 1,
    "AZ-COST-004": 1,
    "AZ-NET-001": 3,
    "AZ-NET-002": 1,
    "AZ-NET-003": 1,
    "AZ-NET-004": 1,
    "AZ-NET-005": 1,
    "AZ-NET-006": 3,
    "AZ-NET-007": 1,
    "AZ-NET-011": 1,
    "AZ-NET-012": 4,
    "AZ-NET-014": 1,
    "AZ-NET-018": 1,
    "AZ-NET-020": 2,
    "AZ-NET-021": 1,
    "AZ-NET-022": 1,
    "AZ-NET-023": 1,
    "AZ-NET-024": 1,
    "AZ-NET-025": 1,
    "AZ-NET-026": 1,
    "AZ-NET-027": 3,
    "AZ-NET-028": 1,
    "AZ-NET-029": 1,
    "AZ-NET-030": 1,
    "AZ-NET-031": 1,
    "AZ-NET-032": 1,
    "AZ-NET-033": 1,
}


@pytest.fixture(scope="module")
def assessment():
    parsed = parse_json(SAMPLE_JSON.read_text(encoding="utf-8"))
    a, doc = assess(normalize(parsed), source_format="arg-json", row_count=parsed.row_count)
    return a, doc


def test_every_portable_rule_fires_and_counts_are_pinned(assessment):
    a, _ = assessment
    counts = Counter(f.rule_id for f in a.findings)
    assert dict(sorted(counts.items())) == EXPECTED_COUNTS
    portable = {k for k, r in RULES.items() if r.applies_to == "export"}
    assert portable == set(EXPECTED_COUNTS)
    assert {u.rule_id for u in a.unknowns} == {k for k, r in RULES.items() if r.applies_to == "live-only"}


def test_summary_is_pinned(assessment):
    a, doc = assessment
    s = a.summary
    assert (s.resource_count, s.row_count, s.subscriptions) == (48, 48, [SUB_HUB, SUB_SPOKE])
    assert s.findings_count == 45 and s.findings_by_severity == {
        "critical": 3,
        "high": 11,
        "medium": 19,
        "low": 10,
        "informational": 2,
    }
    assert s.unknown_rules == 11 and s.rules_evaluated == 34
    assert (
        s.topology.pattern == "hub_spoke" and len(s.topology.hub_vnet_ids) == 2 and len(s.topology.spoke_vnet_ids) == 2
    )
    assert s.rules_version == "2026.10.0" and s.model_version == "lab-1.0.0" and doc["model_version"] == "lab-1.0.0"
    assert len(s.warnings) == 2 and s.by_type["microsoft.network/publicipaddresses"] == 8


def test_resources_carry_their_findings_and_facts(assessment):
    a, _ = assessment
    by_name = {r.name: r for r in a.resources}
    assert len(a.resources) == 48
    nsg = by_name["hcw-sample-nsg-hub"]
    assert sorted(i.split(":")[0] for i in nsg.finding_ids) == ["AZ-NET-020", "AZ-NET-020", "AZ-NET-021"]
    assert by_name["hcw-sample-vnet-spoke1"].facts["peerings"] == 1
    assert {i.split(":")[0] for i in by_name["hcw-sample-vnet-hub"].finding_ids} >= {
        "AZ-NET-011",
        "AZ-NET-024",
        "AZ-NET-012",
    }
    orphan = {r.type for r in a.resources if not r.finding_ids}
    assert orphan.isdisjoint(
        {
            "microsoft.network/virtualnetworks",
            "microsoft.network/azurefirewalls",
        }
    )
    assert "microsoft.network/networkinterfaces" in orphan


def test_findings_serialise_in_camel_case(assessment):
    a, _ = assessment
    doc = a.document()
    f = next(x for x in doc["findings"] if x["ruleId"] == "AZ-NET-003")
    assert set(f) >= {
        "id",
        "ruleId",
        "ruleVersion",
        "severity",
        "category",
        "title",
        "description",
        "resourceId",
        "resourceType",
        "subscriptionId",
        "region",
        "observedState",
        "remediation",
        "learnUrl",
        "frameworkMappings",
        "trafficDirection",
    }
    assert f["observedState"] == {
        "state": "observed",
        "fact": f["observedState"]["fact"],
        "evidenceRef": f["observedState"]["evidenceRef"],
    }
    assert f["subscriptionId"] == SUB_HUB and f["severity"] == "critical"
    assert doc["summary"]["topology"]["hubVnetIds"] and doc["unknowns"][0]["ruleId"]
