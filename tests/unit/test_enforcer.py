# Ported from saulpatinojr/HCW-NetworkEyes_App tests/unit/test_analysis_engine.py (TestObservedStateEnforcer) at
# 5d3b914; changes: the AnalysisEngine fixture is replaced by the registry's evaluate(), which validates every finding.
import pytest

from network_assessment.model.enforcer import ObservedStateEnforcer, ObservedStateViolation, assert_text_is_hedge_free
from network_assessment.model.findings import Finding, FindingSeverity, ObservedState

HEDGE_WORDS = [
    "may",
    "might",
    "could",
    "should",
    "possibly",
    "probably",
    "likely",
    "appears",
    "seems",
    "suggests",
    "indicates",
    "potentially",
    "expected",
    "typically",
    "usually",
    "generally",
]


def test_clean_fact_passes():
    enforcer = ObservedStateEnforcer()
    assert enforcer.scan_text("VNet vnet-001 has no flow logs enabled.") == []


@pytest.mark.parametrize("hedge_word", HEDGE_WORDS)
def test_hedge_words_detected(hedge_word):
    enforcer = ObservedStateEnforcer()
    assert len(enforcer.scan_text(f"This {hedge_word} be a problem.")) > 0


def test_violation_raised_on_finding():
    bad = Finding(
        rule_id="TEST-001",
        severity=FindingSeverity.MEDIUM,
        resource_id="vnet-001",
        resource_type="Microsoft.Network/virtualNetworks",
        title="Test",
        observed_state=ObservedState(fact="This may indicate a misconfiguration.", evidence_ref="test"),
    )
    with pytest.raises(ObservedStateViolation, match="TEST-001"):
        ObservedStateEnforcer().validate(bad)


def test_plain_string_observed_state_is_wrapped():
    f = Finding(severity="high", title="t", observed_state="SecurityRule: direction=Inbound, access=Allow")
    assert f.observed_state.state == "observed" and f.observed_state.evidence_ref == ""
    assert f.model_dump(by_alias=True)["observedState"]["evidenceRef"] == ""


def test_assert_text_is_hedge_free():
    assert_text_is_hedge_free("x", "The subnet has no NSG.")
    with pytest.raises(ObservedStateViolation, match="hedge"):
        assert_text_is_hedge_free("x", "The subnet should have an NSG.")
