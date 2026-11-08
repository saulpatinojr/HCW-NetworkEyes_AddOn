"""The one place this edition imports the assessment engine from (lab-edition code, ADR-0004 and ADR-0006).

The engine is the released wheel of `saulpatinojr/HCW-NetworkEyes_App`: the `network-assessment-azure-engine`
distribution (import name `network_assessment_azure_engine`) or, for the first release `engine-v0.1.0`,
`cna-azure-network-engine` (`cna_azure_network_engine`). `pyproject.toml` pins it by URL and sha256 on the line marked
`# ENGINE_REF`, and `.github/workflows/core-update.yml` writes that pin. The lab's own code (ingestion hand-off, assess,
routes, report, the rule-catalog script) reaches the engine only through this module, and only the wheel's public API
is used (its package `__init__` exports).

There is no fallback: the interim port this module used to run without the wheel was deleted (ADR-0006), so importing
this module without the wheel installed stops the application at startup with EngineNotInstalled.
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


class EngineNotInstalled(ImportError):
    """The engine wheel is not installed, so the lab cannot assess anything and refuses to start."""


def _find_wheel() -> tuple[ModuleType, str]:
    for module, distribution in WHEEL_PACKAGES:
        if importlib.util.find_spec(module) is not None:
            return importlib.import_module(module), distribution
    names = " or ".join(distribution for _, distribution in WHEEL_PACKAGES)
    raise EngineNotInstalled(
        f"the assessment engine is not installed (expected {names}); install the locked dependencies with `uv sync`, "
        "which installs the wheel pinned on the ENGINE_REF line of pyproject.toml"
    )


def _required(module: ModuleType, name: str, since: str) -> Any:
    """``module.name``, or EngineNotInstalled when the installed wheel is older than ``since`` and lacks it."""
    try:
        return getattr(module, name)
    except AttributeError:
        raise EngineNotInstalled(
            f"the installed assessment engine has no {module.__name__}.{name} (added in {since}); install "
            "the locked dependencies with `uv sync`, which installs the wheel pinned on the ENGINE_REF line "
            "of pyproject.toml"
        ) from None


_pkg, DISTRIBUTION = _find_wheel()
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
# The fixed reason a rule carries in unknowns[] when the wheel withheld its finding for hedged wording (since 0.1.4).
HEDGED_WORDING_REASON: str = _required(_rules, "HEDGED_WORDING_REASON", "network-assessment-azure-engine 0.1.4")
RULES_VERSION: str = _pkg.RULES_VERSION
TOPOLOGY_MODEL_VERSION: str = _pkg.TOPOLOGY_MODEL_VERSION
classify_topology = _pkg.classify_topology
evaluate = _pkg.evaluate
rules_table = _pkg.rules_table


def rule_list() -> list[Any]:
    """Every registered rule's metadata, ordered by id (`RuleMeta`: id, title, severity, version, ...)."""
    return list(_rules.rule_metadata())


def describe() -> dict[str, str]:
    """The `engine` block of GET /api/health and GET /api/rules: the wheel's distribution name and version."""
    return {"source": DISTRIBUTION, "version": VERSION}


def rule_count() -> int:
    return len(rule_list())


def live_only_count() -> int:
    return sum(1 for r in rule_list() if r.applies_to == "live-only")


def assert_text_is_hedge_free(label: str, text: str | None) -> None:
    """Raise ObservedStateViolation when a rule text (title, remediation, ...) is empty or carries hedge language.

    This edition's own gate, kept here when the port's enforcer module was deleted: the wheel validates every finding
    at evaluation, and this checks the rule texts the catalog and GET /api/rules show (tests/unit/test_engine.py,
    scripts/rules-doc.py)."""
    if not text:
        raise ObservedStateViolation(f"{label} is empty")
    found = ObservedStateEnforcer().scan_text(text)
    if found:
        raise ObservedStateViolation(f"{label} contains hedge language: {found!r}")


def topology_document(topology: Any) -> dict[str, Any]:
    """The topology as `topology.json` carries it. `model_version` is always present (the wheel calls it
    `schema_version`), so the bundle keeps the key it has always documented."""
    doc = topology.model_dump(mode="json")
    doc.setdefault("model_version", TOPOLOGY_MODEL_VERSION)
    return doc


def normalize(parsed: Any) -> Any:
    """Parsed rows (`ingestion.parse.ParsedRows`) -> the engine's normalised export (`topology`, `rows`, `facts`).

    The wheel's `normalize_rows` takes its own row type and adds its own no-properties warning, so the parser's copy
    of that warning is dropped here. Raises ValueError when the export has no usable `microsoft.network/*` row.
    """
    from network_assessment.ingestion.parse import NO_PROPERTIES_WARNING

    rows: Iterable[Any] = [_normalize.ArgRow(**row.model_dump()) for row in parsed.rows]
    warnings = [w for w in parsed.warnings if w != NO_PROPERTIES_WARNING]
    return _normalize.normalize_rows(rows, warnings=warnings, has_properties=parsed.has_properties)
