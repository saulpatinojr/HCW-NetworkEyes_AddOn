"""The one place this edition imports the assessment engine from (lab-edition code, ADR-0001 and ADR-0004).

Two engines can stand behind this module, and the lab's own code (ingestion hand-off, assess, routes, report, the
rule-catalog script) never needs to know which:

- the released engine wheel, when it is installed: the `network-assessment-azure-engine` distribution (import name
  `network_assessment_azure_engine`) or, for the first release `engine-v0.1.0`, `cna-azure-network-engine`
  (`cna_azure_network_engine`). `pyproject.toml` pins it by URL and sha256 on the line marked `# ENGINE_REF`, and
  `.github/workflows/core-update.yml` writes that pin;
- otherwise the interim port under `network_assessment/{model,rules,classify}` (PROVENANCE.md), which is deleted once a
  bump to the wheel is merged and green (docs/whats-new-upstream.md).

Which one runs is decided by what is installed, so `uv.lock` decides it: a lock without the wheel runs the port, the
bump pull request's lock runs the wheel. Only the wheel's public API is used (its package `__init__` exports).
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
from collections.abc import Iterable
from types import ModuleType
from typing import Any

# Import name -> distribution name, newest name first.
WHEEL_PACKAGES: tuple[tuple[str, str], ...] = (
    ("network_assessment_azure_engine", "network-assessment-azure-engine"),
    ("cna_azure_network_engine", "cna-azure-network-engine"),
)
PORT_SOURCE = "interim port of saulpatinojr/HCW-NetworkEyes_App at 5d3b914"


def _find_wheel() -> tuple[ModuleType, str] | None:
    for module, distribution in WHEEL_PACKAGES:
        if importlib.util.find_spec(module) is not None:
            return importlib.import_module(module), distribution
    return None


_wheel = _find_wheel()

if _wheel is not None:
    _pkg, DISTRIBUTION = _wheel
    VERSION: str = importlib.metadata.version(DISTRIBUTION)
    SOURCE = f"{DISTRIBUTION} {VERSION}"
    _findings = importlib.import_module(f"{_pkg.__name__}.findings")
    _normalize = importlib.import_module(f"{_pkg.__name__}.normalize")
    _rules = importlib.import_module(f"{_pkg.__name__}.rules")

    Finding = _pkg.Finding
    Unknown = _pkg.Unknown
    AzureTopology = _pkg.AzureTopology
    TopologyClassification = _pkg.TopologyClassification
    ObservedStateEnforcer = _findings.ObservedStateEnforcer
    ObservedStateViolation = _findings.ObservedStateViolation
    RULES_VERSION: str = _pkg.RULES_VERSION
    TOPOLOGY_MODEL_VERSION: str = _pkg.TOPOLOGY_MODEL_VERSION
    classify_topology = _pkg.classify_topology
    evaluate = _pkg.evaluate
    rules_table = _pkg.rules_table

    def rule_list() -> list[Any]:
        """Every registered rule's metadata, ordered by id (`RuleMeta`: id, title, severity, version, ...)."""
        return list(_rules.rule_metadata())

else:
    # Module attributes rather than `from ... import`, so both branches bind the same names the same way.
    import network_assessment.classify.topology as _port_classify
    import network_assessment.model.enforcer as _port_enforcer
    import network_assessment.model.findings as _port_findings
    import network_assessment.model.topology as _port_topology
    import network_assessment.rules as _port_rules

    DISTRIBUTION = None
    VERSION = None
    SOURCE = PORT_SOURCE

    Finding = _port_findings.Finding
    Unknown = _port_findings.Unknown
    AzureTopology = _port_topology.AzureTopology
    TopologyClassification = _port_classify.TopologyClassification
    ObservedStateEnforcer = _port_enforcer.ObservedStateEnforcer
    ObservedStateViolation = _port_enforcer.ObservedStateViolation
    RULES_VERSION = _port_rules.RULES_VERSION
    TOPOLOGY_MODEL_VERSION = _port_topology.TOPOLOGY_MODEL_VERSION
    classify_topology = _port_classify.classify_topology
    evaluate = _port_rules.evaluate
    rules_table = _port_rules.rules_table

    def rule_list() -> list[Any]:
        """Every registered rule, ordered by id (`Rule`: id, title, severity, version, ...)."""
        return list(_port_rules.iter_rules())


def is_wheel() -> bool:
    """True when the released engine wheel runs, False for the interim port."""
    return _wheel is not None


def describe() -> dict[str, str | None]:
    """The `engine` block of GET /api/health and GET /api/rules: which engine answers. `source` is the wheel's
    distribution name, or `interim-port` (the port of the App at 5d3b914); `version` is the wheel's version, or null."""
    return {"source": DISTRIBUTION or "interim-port", "version": VERSION}


def rule_count() -> int:
    return len(rule_list())


def live_only_count() -> int:
    return sum(1 for r in rule_list() if r.applies_to == "live-only")


def assert_text_is_hedge_free(label: str, text: str | None) -> None:
    """Raise ObservedStateViolation when a rule text (title, remediation, ...) is empty or carries hedge language."""
    if not text:
        raise ObservedStateViolation(f"{label} is empty")
    found = ObservedStateEnforcer().scan_text(text)
    if found:
        raise ObservedStateViolation(f"{label} contains hedge language: {found!r}")


def topology_document(topology: Any) -> dict[str, Any]:
    """The topology as `topology.json` carries it. `model_version` is always present (the wheel calls it
    `schema_version`), so the bundle's documented key does not depend on which engine ran."""
    doc = topology.model_dump(mode="json")
    doc.setdefault("model_version", TOPOLOGY_MODEL_VERSION)
    return doc


def normalize(parsed: Any) -> Any:
    """Parsed rows (`ingestion.parse.ParsedRows`) -> the engine's normalised export (`topology`, `rows`, `facts`).

    The port uses this edition's normalizer (`ingestion/normalize.py`); the wheel ships the same normalizer, ported
    from it, as `normalize_rows`, which takes its own row type and adds its own no-properties warning.
    Raises ValueError when the export has no usable `microsoft.network/*` row.
    """
    if _wheel is None:
        from network_assessment.ingestion.normalize import normalize as lab_normalize

        return lab_normalize(parsed)
    from network_assessment.ingestion.parse import NO_PROPERTIES_WARNING

    rows: Iterable[Any] = [_normalize.ArgRow(**row.model_dump()) for row in parsed.rows]
    warnings = [w for w in parsed.warnings if w != NO_PROPERTIES_WARNING]
    return _normalize.normalize_rows(rows, warnings=warnings, has_properties=parsed.has_properties)
