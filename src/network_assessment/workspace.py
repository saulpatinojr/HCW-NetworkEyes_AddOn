"""Always-on guided lab workspace provider (ADR-0005).

Every assessment can be handed off to an isolated Linux container workspace via a one-time bundle token.
When CODER_SESSION_TOKEN is configured, the API provisions the workspace directly via the upstream REST API;
otherwise it returns a deep-link launch URL so the visitor's browser session provisions the workspace with
the assessment parameters pre-filled.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from network_assessment.errors import ApiError

WORKSPACE_PROVIDER = "coder"
TIMEOUT_SECONDS = 10.0

Opener = Callable[[urllib.request.Request, float], bytes]


def _default_opener(request: urllib.request.Request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - validated https/http URL
        return response.read()


@dataclass(frozen=True)
class WorkspaceInfo:
    workspace_id: str
    status: Literal["pending", "ready"]
    launch_url: str
    expires_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "workspaceId": self.workspace_id,
            "status": self.status,
            "launchUrl": self.launch_url,
            "expiresAt": self.expires_at,
        }


@dataclass(frozen=True)
class CoderWorkspaceProvider:
    coder_url: str
    template_id: str
    api_base_url: str
    ttl_minutes: int = 240
    session_token: str | None = None
    opener: Opener | None = None
    name: str = WORKSPACE_PROVIDER

    def create_workspace(self, assessment_id: str, bundle_token: str) -> WorkspaceInfo:
        workspace_name = f"na-{assessment_id[:8]}"
        expires_at = (datetime.now(UTC) + timedelta(minutes=self.ttl_minutes)).isoformat().replace("+00:00", "Z")
        base_url = self.coder_url.rstrip("/")

        if self.session_token:
            body = json.dumps(
                {
                    "name": workspace_name,
                    "template_id": self.template_id,
                    "ttl_ms": self.ttl_minutes * 60_000,
                    "rich_parameter_values": [
                        {"name": "assessment_id", "value": assessment_id},
                        {"name": "bundle_token", "value": bundle_token},
                        {"name": "api_base_url", "value": self.api_base_url},
                    ],
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"{base_url}/api/v2/users/me/workspaces",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Coder-Session-Token": self.session_token,
                },
                method="POST",
            )
            try:
                raw = (self.opener or _default_opener)(request, TIMEOUT_SECONDS)
                payload = json.loads(raw.decode("utf-8"))
            except urllib.error.URLError, TimeoutError, OSError, ValueError:
                raise ApiError(
                    502, "workspace_unavailable", "The guided workspace could not be started right now."
                ) from None
            if not isinstance(payload, dict) or not payload.get("id"):
                raise ApiError(502, "workspace_unavailable", "The guided workspace could not be started right now.")
            return WorkspaceInfo(
                workspace_id=str(payload["id"]),
                status="pending",
                launch_url=f"{base_url}/@me/{workspace_name}",
                expires_at=expires_at,
            )

        params = urllib.parse.urlencode(
            {
                "mode": "auto",
                "name": workspace_name,
                "param.assessment_id": assessment_id,
                "param.bundle_token": bundle_token,
                "param.api_base_url": self.api_base_url,
            }
        )
        template_seg = urllib.parse.quote(self.template_id, safe="")
        return WorkspaceInfo(
            workspace_id=workspace_name,
            status="ready",
            launch_url=f"{base_url}/templates/{template_seg}/workspace?{params}",
            expires_at=expires_at,
        )
