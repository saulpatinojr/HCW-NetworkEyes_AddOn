"""The rule registry and the typed rule modules (interim port of the Core's engines, ADR-0001; see PROVENANCE.md).

Importing this package registers every rule: the modules are imported for their decorators' side effect.
"""

from network_assessment.rules import azure_bcdr, azure_cost, azure_net  # noqa: F401 - registration
from network_assessment.rules.registry import (
    RULES,
    RULES_VERSION,
    EvaluationResult,
    Rule,
    evaluate,
    iter_rules,
    rules_table,
)

__all__ = ["RULES", "RULES_VERSION", "EvaluationResult", "Rule", "evaluate", "iter_rules", "rules_table"]
