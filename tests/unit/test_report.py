import io
import json
import zipfile

import pytest

from network_assessment.assess import assess
from network_assessment.ingestion import normalize, parse_json
from network_assessment.model.enforcer import ObservedStateEnforcer
from network_assessment.report import BUNDLE_FILES, NOT_FOR_PRODUCTION, make_bundle, render_markdown, zip_bytes
from network_assessment.report.markdown import CANNOT_SHOW

from ..conftest import SAMPLE_JSON


@pytest.fixture(scope="module")
def built():
    parsed = parse_json(SAMPLE_JSON.read_text(encoding="utf-8"))
    a, doc = assess(normalize(parsed), source_format="arg-json", file_name="my export.json", row_count=parsed.row_count)
    return a, make_bundle(a, doc)


def test_markdown_sections(built):
    a, files = built
    md = files["report.md"].decode()
    for heading in (
        "# Network assessment report",
        "## Scope",
        "## Summary",
        "## Topology",
        "## Findings by severity",
        "## Rules this export cannot answer",
        "## What this cannot show".replace("this", "this export"),
        "## Notice",
    ):
        assert heading in md, heading
    assert "Pattern: **hub_spoke**" in md and "my export.json" in md and "[VERIFY]" in md
    assert md.index("### CRITICAL") < md.index("### HIGH") < md.index("### INFORMATIONAL")
    assert all(item in md for item in CANNOT_SHOW)
    assert "| AZ-NET-008 |" in md and "AZ-COST-002" in md


def test_bundle_entries_and_zip(built):
    a, files = built
    assert tuple(sorted(files)) == tuple(sorted(BUNDLE_FILES))
    findings = json.loads(files["findings.json"])
    assert len(findings["findings"]) == 45 and len(findings["unknowns"]) == 11
    assert json.loads(files["topology.json"])["model_version"] == "lab-1.0.0"
    assert json.loads(files["summary.json"])["rulesVersion"] == "2026.10.0"
    rules = json.loads(files["rules.json"])
    assert rules["rulesVersion"] == "2026.10.0" and len(rules["rules"]) == 45
    assert (
        files["NOT-FOR-PRODUCTION.md"].decode() == NOT_FOR_PRODUCTION
        and "| `report.md` |" in files["README.md"].decode()
    )
    z = zipfile.ZipFile(io.BytesIO(zip_bytes(files)))
    assert sorted(z.namelist()) == sorted(BUNDLE_FILES)
    assert all(i.compress_type == zipfile.ZIP_STORED and i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist())


def test_zip_rejects_traversal():
    with pytest.raises(ValueError):
        zip_bytes({"../x": b""})
    with pytest.raises(ValueError):
        zip_bytes({"/abs": b""})


def test_report_facts_are_hedge_free(built):
    a, _ = built
    enforcer = ObservedStateEnforcer()
    for f in a.findings:
        assert enforcer.scan_text(f.observed_state.fact) == [], f.id
        assert enforcer.scan_text(f.title) == [] and enforcer.scan_text(f.remediation or "") == []


def test_empty_assessment_renders():
    from datetime import UTC, datetime

    from network_assessment.report.summary import Assessment, Summary, TopologySummary

    a = Assessment(
        id="x",
        created_at=datetime(2026, 10, 10, tzinfo=UTC),
        source_format="arg-json",
        rules_version="v",
        model_version="m",
        summary=Summary(
            resource_count=0,
            row_count=0,
            subscriptions=[],
            by_type={},
            topology=TopologySummary(pattern="isolated"),
            findings_count=0,
            findings_by_severity={},
            unknown_rules=0,
            rules_evaluated=0,
            warnings=[],
            rules_version="v",
            model_version="m",
            generated_at=datetime(2026, 10, 10, tzinfo=UTC),
        ),
        findings=[],
        resources=[],
        unknowns=[],
        warnings=[],
    )
    md = render_markdown(a)
    assert "No finding was observed." in md and "Every registered rule was evaluated" in md
