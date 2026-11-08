"""What this edition needs from the engine it runs (`network_assessment.engine`: the released wheel, the only engine
since the interim port was deleted, ADR-0006).

These tests run against the wheel `uv.lock` installs, so on a core-update bump pull request they are the
compatibility check for an engine release: rule ids, versions, severities and `applies_to` (ADR-0004), the
live-only rules staying registered so `unknowns[]` is stable, complete and hedge-free rule texts for the catalog and
GET /api/rules, `export:` evidence references (docs/api/openapi.yaml) and the topology model marker. They also prove
the lab refuses to start without the wheel instead of falling back to anything.
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from network_assessment import engine
from network_assessment.assess import assess
from network_assessment.ingestion import parse_csv, parse_json

from ..conftest import EXPECTED_MODEL_VERSION, MODEL_VERSIONS, ROOT, SAMPLE_CSV, SAMPLE_JSON, SAMPLE_PORTAL_CSV

# The digest of every rule's id|version|severity|applies_to, in id order; it moves only with RULES_VERSION.
REGISTRY_DIGEST = "dd1d1f26a4e80db1fb786ea4bd71374a449522e4fb13999855477d8a994c4add"
EXPECTED_RULES_VERSION = "2026.11.0"
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
    """The ENGINE_REF value (a version) and its whole line in pyproject.toml."""
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
    assert engine.SOURCE.split(" ") == [engine.DISTRIBUTION, engine.VERSION]


def test_the_engine_that_runs_is_the_one_pyproject_pins():
    ref, line = _engine_ref()
    assert ref != "none", "the interim port is gone (ADR-0006): pyproject.toml must pin an engine wheel"
    assert ref == engine.VERSION, f"ENGINE_REF {ref}, but {engine.SOURCE} runs"
    assert line.strip().startswith(f'"{engine.DISTRIBUTION} @ https://github.com/'), line
    assert f"/engine-v{ref}/" in line and line.rstrip().endswith(f"ENGINE_REF {ref}"), line
    assert engine.describe() == {"source": engine.DISTRIBUTION, "version": engine.VERSION}


def test_without_the_wheel_the_lab_refuses_to_start(monkeypatch):
    # No fallback engine exists any more, so a missing wheel is a startup error that says what to do, not a
    # silent switch to something else.
    monkeypatch.setattr(engine.importlib.util, "find_spec", lambda name, *a, **k: None)
    with pytest.raises(engine.EngineNotInstalled, match="ENGINE_REF") as caught:
        engine._find_wheel()
    assert isinstance(caught.value, ImportError)
    for _, distribution in engine.WHEEL_PACKAGES:
        assert distribution in str(caught.value)


def test_the_application_does_not_start_without_the_wheel():
    # A fresh interpreter in which neither engine name can be imported (a None entry in sys.modules makes
    # importlib.util.find_spec answer None): importing the application fails with EngineNotInstalled.
    hide = "; ".join(f"sys.modules[{module!r}] = None" for module, _ in engine.WHEEL_PACKAGES)
    code = f"import sys; {hide}; import network_assessment.app"
    run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60, check=False)
    assert run.returncode != 0
    assert "EngineNotInstalled" in run.stderr and "ENGINE_REF" in run.stderr, run.stderr[-500:]


def test_an_empty_rule_text_is_refused():
    for empty in ("", None):
        with pytest.raises(engine.ObservedStateViolation, match="is empty"):
            engine.assert_text_is_hedge_free("AZ-TEST-001.title", empty)


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
