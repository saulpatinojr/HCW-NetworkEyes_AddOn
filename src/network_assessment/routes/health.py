"""GET /api/health: the flat standard envelope, answered without any upstream dependency."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from network_assessment import ADDON_ID, __version__
from network_assessment.edition import AZURE_CONNECTIVITY, CAPABILITIES, EDITION
from network_assessment.engine import RULES_VERSION, TOPOLOGY_MODEL_VERSION, live_only_count, rule_count
from network_assessment.workspace import WORKSPACE_PROVIDER

router = APIRouter()


def health_body(request: Request) -> dict:
    settings = request.app.state.settings
    live_only = live_only_count()
    return {
        "ok": True,
        "id": ADDON_ID,
        "version": __version__,
        "edition": EDITION,
        "capabilities": list(CAPABILITIES),
        "asOf": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "siteOrigins": list(settings.site_origins),
        "turnstile": {"required": settings.turnstile_enforced, "siteKey": settings.turnstile_site_key},
        "workspace": WORKSPACE_PROVIDER,
        "azureConnectivity": AZURE_CONNECTIVITY,
        "rules": {"version": RULES_VERSION, "count": rule_count(), "liveOnly": live_only},
        "model": {"version": TOPOLOGY_MODEL_VERSION},
        "limits": {
            "maxUploadBytes": settings.max_upload_bytes,
            "maxRows": settings.max_rows,
            "ttlMinutes": settings.ttl_minutes,
        },
    }


@router.get("/api/health")
async def health(request: Request) -> dict:
    return health_body(request)
