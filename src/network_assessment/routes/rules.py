"""GET /api/rules: the registry the pane lists (titles, severities, evidence, remediation, links; never evaluator
code)."""

from __future__ import annotations

from fastapi import APIRouter

from network_assessment.model.topology import TOPOLOGY_MODEL_VERSION
from network_assessment.rules.registry import RULES, RULES_VERSION, rules_table

router = APIRouter()


@router.get("/api/rules")
async def rules() -> dict:
    table = rules_table()
    return {
        "version": RULES_VERSION,
        "modelVersion": TOPOLOGY_MODEL_VERSION,
        "count": len(RULES),
        "liveOnly": sum(1 for r in table if r["appliesTo"] == "live-only"),
        "verify": True,
        "rules": table,
    }
