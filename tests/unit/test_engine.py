"""What this edition needs from the engine it runs, whichever it is (`network_assessment.engine`: the released wheel
when installed, the interim port otherwise).

These tests run against the port today and against the wheel on the core-update bump pull request, so they are the
compatibility check for an engine release: rule ids, versions, severities and `applies_to` (ADR-0004), the
live-only rules staying registered so `unknowns[]` is stable, complete and hedge-free rule texts for the catalog and
GET /api/rules, `export:` evidence references (docs/api/openapi.yaml), the topology model marker, and the same
normalised export as this edition's own normalizer.
"""

import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from network_assessment import engine
from network_assessment.assess import assess
from network_assessment.ingestion import parse_csv, parse_json

from ..conftest import EXPECTED_MODEL_VERSION, MODEL_VERSIONS, ROOT, SAMPLE_CSV, SAMPLE_JSON, SAMPLE_PORTAL_CSV

# Same digest and formula as tests/unit/test_registry.py (which tests the port itself): id|version|severity|applies_to.
REGISTRY_DIGEST = "7424a4a3ffb04be3328629889924bc31d88afbe2d576bd71f389f8d242b71339"
EXPECTED_RULES_VERSION = "2026.10.0"
LIVE_ONLY = {
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
SAMPLES = (SAMPLE_JSON, SAMPLE_CSV, SAMPLE_PORTAL_CSV)
# The hedge words this edition refuses in every rule text and finding fact. Owned here, not by the engine: an engine
# release whose enforcer stops flagging one of them fails test_the_enforcer_refuses_every_hedge_word_this_edition_needs.
EDITION_HEDGE_WORDS = (
    "may",
    "might",
    "could",
    "should",
    "possibly",
    "probably",
    "likely",
    "appears",
    "seems",
    "suggest",
    "suggests",
    "indicates",
    "potentially",
    "expected",
    "typically",
    "usually",
    "generally",
)


def _engine_ref() -> tuple[str, str]:
    """The ENGINE_REF value (`none` or a version) and its whole line in pyproject.toml."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lines = [x for x in text.splitlines() if re.search(r"#\s*ENGINE_REF\s", x)]  # the marker core-update.yml reads
    assert len(lines) == 1, "pyproject.toml must carry exactly one ENGINE_REF line"
    found = re.search(r"#\s*ENGINE_REF\s+([0-9A-Za-z][0-9A-Za-z.+-]*)", lines[0])
    assert found, lines[0]
    return found.group(1), lines[0]


def _parse(path: Path):
    text = path.read_text(encoding="utf-8")
    return parse_json(text) if path.suffix == ".json" else parse_csv(text)


def test_the_engine_is_one_this_edition_knows():
    assert engine.SOURCE in MODEL_VERSIONS, f"{engine.SOURCE}: add its model version to tests/conftest.py"
    assert engine.TOPOLOGY_MODEL_VERSION == EXPECTED_MODEL_VERSION
    assert engine.is_wheel() == (engine.SOURCE != engine.PORT_SOURCE)


def test_the_engine_that_runs_is_the_one_pyproject_pins():
    ref, line = _engine_ref()
    assert engine.is_wheel() == (ref != "none"), f"ENGINE_REF {ref}, but {engine.SOURCE} runs"
    if ref == "none":
        assert engine.VERSION is None and engine.DISTRIBUTION is None
        assert line.strip().startswith("#"), "before the first adoption the line is only the marker"
    else:
        assert ref == engine.VERSION
        assert line.strip().startswith(f'"{engine.DISTRIBUTION} @ https://github.com/'), line
        assert f"/engine-v{ref}/" in line and line.rstrip().endswith(f"ENGINE_REF {ref}"), line
    assert engine.describe() == {"source": engine.DISTRIBUTION or "interim-port", "version": engine.VERSION}


@pytest.mark.parametrize("word", EDITION_HEDGE_WORDS)
def test_the_enforcer_refuses_every_hedge_word_this_edition_needs(word):
    enforcer = engine.ObservedStateEnforcer()
    for text in (f"The gateway {word} be exposed.", f"{word.capitalize()} the subnet is open."):
        assert enforcer.scan_text(text), f"the active enforcer does not flag {word!r} in {text!r}"
        with pytest.raises(engine.ObservedStateViolation):
            engine.assert_text_is_hedge_free("test", text)
    assert not enforcer.scan_text("The gateway is exposed."), "a plain statement must pass"


def test_rule_ids_versions_severities_and_applies_to_are_pinned():
    rules = engine.rule_list()
    assert [r.id for r in rules] == sorted(r.id for r in rules)
    digest = hashlib.sha256(
        "\n".join(f"{r.id}|{r.version}|{r.severity.value}|{r.applies_to}" for r in rules).encode()
    ).hexdigest()
    assert (digest, engine.RULES_VERSION) == (REGISTRY_DIGEST, EXPECTED_RULES_VERSION)
    assert engine.rule_count() == 45 and engine.live_only_count() == len(LIVE_ONLY)
    assert {r.id for r in rules if r.applies_to == "live-only"} == LIVE_ONLY


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.name)
def test_live_only_rules_are_reported_as_unknown_never_dropped(path):
    parsed = _parse(path)
    a, _ = assess(engine.normalize(parsed), source_format="test", row_count=parsed.row_count)
    unknown = {u.rule_id for u in a.unknowns}
    assert unknown >= LIVE_ONLY
    assert {f.rule_id for f in a.findings}.isdisjoint(unknown)
    assert all(u.reason for u in a.unknowns)


@pytest.mark.parametrize("rule_id", sorted(r.id for r in engine.rule_list()))
def test_every_rule_text_is_present_and_hedge_free(rule_id):
    r = next(x for x in engine.rule_list() if x.id == rule_id)
    for label in ("title", "description", "remediation", "evidence"):
        engine.assert_text_is_hedge_free(f"{rule_id}.{label}", getattr(r, label))
    parts = urlsplit(r.learn_url)
    assert parts.scheme == "https" and parts.hostname == "learn.microsoft.com", r.learn_url
    assert r.frameworks and r.category


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.name)
def test_findings_cite_the_export_and_state_facts_only(path):
    parsed = _parse(path)
    a, _ = assess(engine.normalize(parsed), source_format="test", row_count=parsed.row_count)
    enforcer = engine.ObservedStateEnforcer()
    for f in a.findings:
        assert f.observed_state.evidence_ref.startswith("export:"), (f.id, f.observed_state.evidence_ref)
        assert not enforcer.scan_text(f.observed_state.fact), f.id
        assert f.title and f.description and f.remediation, f.id


@pytest.mark.skipif(not engine.is_wheel(), reason="only meaningful while the wheel runs beside the interim port")
@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.name)
def test_the_wheel_normalises_exactly_like_this_edition(path):
    # Deleted with the interim port: ingestion/normalize.py builds the port's model.
    from network_assessment.ingestion.normalize import normalize as lab_normalize

    parsed = _parse(path)
    lab, wheel = lab_normalize(parsed), engine.normalize(parsed)
    assert wheel.facts == lab.facts
    assert wheel.topology.warnings == lab.topology.warnings
    lab_doc = lab.topology.model_dump(mode="json")
    wheel_doc = wheel.topology.model_dump(mode="json")

    def same_fields(ours, theirs):
        if isinstance(ours, dict) and isinstance(theirs, dict):
            return {k: same_fields(v, theirs.get(k)) for k, v in ours.items() if k != "model_version"}
        if isinstance(ours, list) and isinstance(theirs, list) and len(ours) == len(theirs):
            return [same_fields(o, t) for o, t in zip(ours, theirs, strict=True)]
        return theirs

    assert same_fields(lab_doc, wheel_doc) == {k: v for k, v in lab_doc.items() if k != "model_version"}
