"""GET /api/config: public widget settings for the pane."""

from __future__ import annotations

from fastapi import APIRouter, Request

from network_assessment.config import TURNSTILE_ACTION
from network_assessment.workspace import WORKSPACE_PROVIDER

router = APIRouter()


@router.get("/api/config")
async def config(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "turnstileSiteKey": settings.turnstile_site_key,
        "turnstileRequired": settings.turnstile_enforced,
        "turnstileAction": TURNSTILE_ACTION,
        "workspace": WORKSPACE_PROVIDER,
        "limits": {"maxUploadBytes": settings.max_upload_bytes, "maxRows": settings.max_rows},
        "ttlMinutes": settings.ttl_minutes,
        "siteOrigins": list(settings.site_origins),
    }
