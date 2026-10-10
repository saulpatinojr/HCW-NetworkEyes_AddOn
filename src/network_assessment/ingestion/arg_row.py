"""One Resource Graph row as the export carries it: `type` lower-cased, `properties` a dict, ids derived when absent."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ID_RG = re.compile(r"^/subscriptions/([^/]+)/resourcegroups/([^/]+)/", re.IGNORECASE)
_ID_SUB = re.compile(r"^/subscriptions/([^/]+)", re.IGNORECASE)


class ArgRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    type: str
    location: str | None = None
    resource_group: str | None = None
    subscription_id: str | None = None
    kind: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    zones: list[str] = Field(default_factory=list)
    sku: dict[str, Any] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    row: int = 0  # 1-based position in the export, for warnings

    @field_validator("type")
    @classmethod
    def _lower_type(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def short_type(self) -> str:
        return self.type.removeprefix("microsoft.network/")

    @property
    def prop(self) -> dict[str, Any]:
        return self.properties


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): ("" if v is None else str(v)) for k, v in value.items()}


def row_from_dict(raw: dict[str, Any], index: int) -> ArgRow | None:
    """Build an ArgRow or return None when the row has no usable type or id/name."""
    rtype = _opt_str(raw.get("type"))
    if not rtype:
        return None
    rid = _opt_str(raw.get("id"))
    name = _opt_str(raw.get("name"))
    rg = _opt_str(raw.get("resourceGroup"))
    sub = _opt_str(raw.get("subscriptionId"))
    if rid:
        m = _ID_RG.match(rid)
        if m:
            sub = sub or m.group(1)
            rg = rg or m.group(2)
        else:
            m2 = _ID_SUB.match(rid)
            if m2:
                sub = sub or m2.group(1)
        if not name:
            name = rid.rstrip("/").rsplit("/", 1)[-1]
    else:
        if not name:
            return None
        rid = f"/subscriptions/{sub or 'unknown'}/resourceGroups/{rg or 'unknown'}/providers/{rtype}/{name}"
    zones_raw = raw.get("zones")
    zones = [str(z) for z in zones_raw] if isinstance(zones_raw, list) else []
    return ArgRow(
        id=rid,
        name=name,
        type=rtype,
        location=_opt_str(raw.get("location")),
        resource_group=rg,
        subscription_id=sub,
        kind=_opt_str(raw.get("kind")),
        tags=_str_dict(raw.get("tags")),
        zones=zones,
        sku=raw.get("sku") if isinstance(raw.get("sku"), dict) else {},
        properties=raw.get("properties") if isinstance(raw.get("properties"), dict) else {},
        row=index,
    )
