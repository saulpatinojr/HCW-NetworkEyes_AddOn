"""Registry invariants: unique ids, complete metadata, hedge-free texts, hash-pinned RULES_VERSION, dedup, unknowns."""

import hashlib
from urllib.parse import urlsplit

import pytest

from network_assessment.model.enforcer import assert_text_is_hedge_free
from network_assessment.model.topology import AzureTopology
from network_assessment.rules import RULES, RULES_VERSION, evaluate, rules_table
from network_assessment.rules.registry import Emit, NotEvaluable, Rule, _register, iter_rules, rule
from network_assessment.rules.taxonomy import classify_traffic_direction

from .model_fixtures import SUB, subscription, topology, vnet

# Pinned registry digest: ids, versions, severities, applies_to. When the rule set changes, RULES_VERSION changes too.
REGISTRY_DIGEST = "7424a4a3ffb04be3328629889924bc31d88afbe2d576bd71f389f8d242b71339"
EXPECTED_VERSION = "2026.10.0"


def test_rules_version_is_pinned_to_the_rule_set():
    digest = hashlib.sha256(
        "\n".join(f"{r.id}|{r.version}|{r.severity.value}|{r.applies_to}" for r in iter_rules()).encode()
    ).hexdigest()
    assert (digest, RULES_VERSION) == (REGISTRY_DIGEST, EXPECTED_VERSION), (
        "the rule set changed: bump RULES_VERSION and re-pin REGISTRY_DIGEST"
    )


def test_registry_shape_and_counts():
    ids = [r.id for r in iter_rules()]
    assert len(ids) == len(set(ids)) == 45
    assert sum(1 for r in RULES.values() if r.applies_to == "live-only") == 11
    net = sorted(i for i in ids if i.startswith("AZ-NET-"))
    assert net == [f"AZ-NET-{n:03d}" for n in range(1, 34)]
    assert sorted(i for i in ids if i.startswith("AZ-BCDR-")) == [f"AZ-BCDR-{n:03d}" for n in range(1, 8)]
    assert sorted(i for i in ids if i.startswith("AZ-COST-")) == [f"AZ-COST-{n:03d}" for n in range(1, 6)]
    live = {r.id for r in RULES.values() if r.applies_to == "live-only"}
    assert live == {
        "AZ-NET-008",
        "AZ-NET-009",
        "AZ-NET-010",
        "AZ-NET-013",
        "AZ-NET-015",
        "AZ-NET-016",
        "AZ-NET-017",
        "AZ-NET-019",
        "AZ-COST-002",
        "AZ-COST-003",
        "AZ-COST-005",
    }


@pytest.mark.parametrize("rule_id", sorted(RULES))
def test_every_rule_is_complete_and_hedge_free(rule_id):
    r = RULES[rule_id]
    assert r.title and r.remediation and r.description and r.evidence and r.frameworks
    parts = urlsplit(r.learn_url)
    assert parts.scheme == "https" and parts.hostname == "learn.microsoft.com", r.learn_url
    assert r.version >= 1 and r.category
    for label in ("title", "remediation", "description", "evidence"):
        assert_text_is_hedge_free(f"{rule_id}.{label}", getattr(r, label))
    assert classify_traffic_direction(rule_id) in ("east_west", "north_south", "management")


def test_rules_table_serialises_the_registry():
    table = rules_table()
    assert [row["id"] for row in table] == [r.id for r in iter_rules()]
    row = next(x for x in table if x["id"] == "AZ-NET-003")
    assert set(row) == {
        "id",
        "title",
        "severity",
        "category",
        "version",
        "appliesTo",
        "evidence",
        "needsProperties",
        "description",
        "remediation",
        "learnUrl",
        "frameworks",
    }
    assert row["severity"] == "critical" and row["version"] == 2 and row["frameworks"][0]["framework"]


def test_evaluate_dedups_on_rule_and_resource_and_surfaces_live_only():
    v = vnet("a")
    result = evaluate(topology(subscription(vnets=[v]), subscription(sub=SUB, vnets=[v])))
    assert [f.id for f in result.findings if f.rule_id == "AZ-NET-001"] == [f"AZ-NET-001:{v.id}"]
    assert {u.rule_id for u in result.unknowns} >= {"AZ-NET-008", "AZ-COST-002", "AZ-NET-006"}
    assert all(f.observed_state.state == "observed" and f.framework_mappings for f in result.findings)


def test_no_properties_export_answers_unknown_for_property_rules():
    result = evaluate(AzureTopology(subscriptions=[subscription(vnets=[vnet("a")])], has_properties=False))
    unknown = {u.rule_id: u.reason for u in result.unknowns}
    assert "AZ-NET-001" in unknown and "no properties column" in unknown["AZ-NET-001"]
    assert {f.rule_id for f in result.findings} == {"AZ-NET-033"}


def test_registration_guards(monkeypatch):
    with pytest.raises(ValueError, match="duplicate"):
        rule(
            id="AZ-NET-001",
            title="t",
            severity="low",
            category="c",
            version=1,
            learn_url="https://learn.microsoft.com/",
            frameworks=RULES["AZ-NET-001"].frameworks,
            evidence="e",
            remediation="r",
            description="d",
        )(lambda sub, topo: iter(()))
    with pytest.raises(ValueError, match="evaluator"):
        _register(
            Rule(
                id="X-1",
                title="t",
                severity="low",
                category="c",
                version=1,
                learn_url="https://learn.microsoft.com/",
                frameworks=RULES["AZ-NET-001"].frameworks,
                applies_to="export",
                evidence="e",
                remediation="r",
                description="d",
            )
        )
    with pytest.raises(ValueError, match="framework"):
        _register(
            Rule(
                id="X-2",
                title="t",
                severity="low",
                category="c",
                version=1,
                learn_url="https://learn.microsoft.com/",
                frameworks=(),
                applies_to="live-only",
                evidence="e",
                remediation="r",
                description="d",
            )
        )
    assert "X-1" not in RULES and "X-2" not in RULES


def test_hedge_language_in_a_fact_fails_evaluation(monkeypatch):
    from network_assessment.model.enforcer import ObservedStateViolation

    def bad(sub, topo):
        yield Emit(resource_id="r", resource_type="t", fact="This may be wrong.", evidence_ref="x")

    monkeypatch.setitem(
        RULES, "AZ-NET-001", RULES["AZ-NET-001"].__class__(**{**RULES["AZ-NET-001"].__dict__, "func": bad})
    )
    with pytest.raises(ObservedStateViolation):
        evaluate(topology(subscription(vnets=[vnet("a")])))


def test_not_evaluable_records_the_first_reason_once(monkeypatch):
    def unsure(sub, topo):
        yield NotEvaluable("first")
        yield NotEvaluable("second")

    monkeypatch.setitem(
        RULES, "AZ-NET-001", RULES["AZ-NET-001"].__class__(**{**RULES["AZ-NET-001"].__dict__, "func": unsure})
    )
    result = evaluate(topology(subscription(vnets=[vnet("a")]), subscription(sub="x", vnets=[vnet("b", sub="x")])))
    assert [u.reason for u in result.unknowns if u.rule_id == "AZ-NET-001"] == ["first"]


def test_taxonomy_fallbacks():
    assert classify_traffic_direction("", "Network Segmentation") == "east_west"
    assert classify_traffic_direction("", "", "Microsoft.Network/bastionHosts") == "management"
    assert classify_traffic_direction("", "", "Microsoft.Network/publicIPAddresses") == "north_south"
    assert classify_traffic_direction("AZ-COST-099") == "north_south"
    assert classify_traffic_direction("", "", "") == "" and classify_traffic_direction("NOPE", "x", "y") == ""
