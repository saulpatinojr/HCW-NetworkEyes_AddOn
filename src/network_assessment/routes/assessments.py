"""POST/GET/DELETE /api/assessments: the only mutating surface, gated by human verification and the limits."""

from __future__ import annotations

import json
import re
import time
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from network_assessment.assess import assess
from network_assessment.engine import normalize
from network_assessment.errors import ApiError
from network_assessment.ingestion import (
    InvalidExport,
    ParsedRows,
    TooManyRows,
    parse_csv,
    parse_document,
    parse_json,
)
from network_assessment.report import BUNDLE_FILES, make_bundle, zip_bytes
from network_assessment.security.limits import client_address, read_body
from network_assessment.security.logging import log_event
from network_assessment.security.turnstile import verify

router = APIRouter()

FILE_NAME = re.compile(r"^[\w .()-]{1,120}\.(json|csv)$")
CONTENT_TYPES = {"md": "text/markdown; charset=utf-8", "json": "application/json"}


class CreateAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["arg-json", "arg-csv"]
    content: str = Field(min_length=1)
    fileName: str | None = Field(default=None, pattern=FILE_NAME.pattern)


def _owner_token(request: Request) -> str | None:
    token = request.headers.get("x-owner-token", "").strip()
    return token if 0 < len(token) <= 128 else None


def _bundle_token(request: Request) -> str | None:
    token = request.headers.get("x-bundle-token", "").strip()
    return token if 0 < len(token) <= 128 else None


def _expires_at(state, assessment) -> str:
    return (assessment.created_at + timedelta(minutes=state.settings.ttl_minutes)).isoformat().replace("+00:00", "Z")


def _parse_upload(body: bytes, content_type: str, max_rows: int) -> tuple[str, ParsedRows, str | None]:
    """Returns (format, parsed_rows, file_name)."""
    if content_type.startswith("text/csv"):
        text = body.decode("utf-8", errors="replace")
        return "arg-csv", parse_csv(text, max_rows=max_rows), None
    try:
        document = json.loads(body.decode("utf-8"))
    except UnicodeDecodeError, json.JSONDecodeError:
        raise ApiError(400, "invalid_json", "The body is not valid JSON.") from None
    if isinstance(document, dict) and "format" in document and "data" not in document:
        try:
            wrapper = CreateAssessmentRequest.model_validate(document)
        except ValidationError as exc:
            fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
            raise ApiError(400, "invalid_request", "The request shape is not valid.", {"fields": fields}) from None
        if wrapper.format == "arg-csv":
            return "arg-csv", parse_csv(wrapper.content, max_rows=max_rows), wrapper.fileName
        return "arg-json", parse_json(wrapper.content, max_rows=max_rows), wrapper.fileName
    return "arg-json", parse_document(document, max_rows=max_rows), None


@router.post("/api/assessments", status_code=201)
async def create_assessment(request: Request) -> Response:
    state = request.app.state
    settings = state.settings
    started = time.monotonic()

    allowed, retry_after = state.limiter.acquire(client_address(request, settings.trust_proxy))
    if not allowed:
        log_event("rate_limited", retryAfter=retry_after)
        raise ApiError(
            429,
            "rate_limited",
            "Too many uploads from this client; try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in ("application/json", "text/csv"):
        raise ApiError(415, "unsupported_media_type", "Send application/json or text/csv.")

    if settings.turnstile_required:
        verdict = verify(
            settings.turnstile_secret or "",
            request.headers.get("x-turnstile-token"),
            client_address(request, settings.trust_proxy),
            expected_hostname=settings.public_host,
            opener=state.verifier,
        )
        if not verdict.ok:
            log_event("turnstile_rejected", codes=len(verdict.codes))
            raise ApiError(403, "turnstile_failed", "Human verification did not succeed.", {"codes": verdict.codes})
        log_event("turnstile_verified")
    elif settings.turnstile_enforced:
        raise ApiError(
            503, "turnstile_not_configured", "Uploads are not available until human verification is configured."
        )

    body = await read_body(request, settings.max_upload_bytes)
    try:
        fmt, parsed, file_name = _parse_upload(body, content_type, settings.max_rows)
    except TooManyRows as exc:
        log_event("assessment_rejected", code="too_many_rows", rows=exc.count)
        raise ApiError(
            422,
            "too_many_rows",
            "The export has more rows than the limit.",
            {"rows": exc.count, "maxRows": exc.max_rows},
        ) from None
    except InvalidExport as exc:
        log_event("assessment_rejected", code="invalid_export")
        raise ApiError(
            400,
            "invalid_export",
            "This file is not a Resource Graph export; use the export commands in the user guide.",
            {"reason": str(exc)},
        ) from None
    try:
        normalized = normalize(parsed)
    except ValueError as exc:
        log_event("assessment_rejected", code="ingestion_failed", warnings=len(parsed.warnings))
        raise ApiError(
            422,
            "ingestion_failed",
            "The export could not be read.",
            {"reason": str(exc), "warnings": parsed.warnings[:50]},
        ) from None

    if not await state.bound.acquire():
        log_event("overloaded")
        raise ApiError(503, "overloaded", "The service is busy; try again shortly.", headers={"Retry-After": "2"})
    try:
        assessment, topology_document = assess(
            normalized, source_format=fmt, file_name=file_name, row_count=parsed.row_count
        )
        files = make_bundle(assessment, topology_document)
        files["bundle.zip"] = zip_bytes(files)
    finally:
        state.bound.release()

    stored = state.store.put(assessment, files)
    log_event(
        "assessment_created",
        format=fmt,
        rows=parsed.row_count,
        resources=assessment.summary.resource_count,
        findings=len(assessment.findings),
        unknowns=len(assessment.unknowns),
        warnings=len(assessment.warnings),
        durationMs=int((time.monotonic() - started) * 1000),
        stored=state.store.size,
    )
    payload = {
        "assessmentId": stored.id,
        "ownerToken": stored.owner_token,
        "expiresAt": _expires_at(state, assessment),
        "summary": assessment.summary.model_dump(mode="json", by_alias=True),
        "ingestionWarnings": list(assessment.warnings),
    }
    return Response(json.dumps(payload), status_code=201, media_type="application/json")


def _load(request: Request, assessment_id: str):
    entry = request.app.state.store.get(assessment_id, _owner_token(request))
    if entry is None:
        raise ApiError(404, "not_found", "Not found.")
    return entry


@router.get("/api/assessments/{assessment_id}")
async def get_assessment(request: Request, assessment_id: str) -> Response:
    assessment, files = _load(request, assessment_id)
    log_event("assessment_read")
    body: dict[str, Any] = {
        "assessment": assessment.document(),
        "files": sorted(files),
        "expiresAt": _expires_at(request.app.state, assessment),
    }
    return Response(json.dumps(body), media_type="application/json")


@router.get("/api/assessments/{assessment_id}/report.md")
async def get_report_md(request: Request, assessment_id: str) -> Response:
    _, files = _load(request, assessment_id)
    return Response(
        files["report.md"],
        media_type=CONTENT_TYPES["md"],
        headers={"Content-Disposition": f'attachment; filename="assessment-{assessment_id[:8]}.md"'},
    )


@router.get("/api/assessments/{assessment_id}/report.json")
async def get_report_json(request: Request, assessment_id: str) -> Response:
    assessment, _ = _load(request, assessment_id)
    body = assessment.document()
    body["expiresAt"] = _expires_at(request.app.state, assessment)
    return Response(json.dumps(body), media_type="application/json")


@router.get("/api/assessments/{assessment_id}/bundle.zip")
async def get_bundle(request: Request, assessment_id: str) -> Response:
    owner_token = _owner_token(request)
    if owner_token is not None:
        _, files = _load(request, assessment_id)
    else:
        entry = request.app.state.store.redeem_bundle_token(assessment_id, _bundle_token(request))
        if entry is None:
            raise ApiError(404, "not_found", "Not found.")
        _, files = entry
    return Response(
        files["bundle.zip"],
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="assessment-{assessment_id[:8]}.zip"'},
    )


@router.get("/api/assessments/{assessment_id}/files/{path:path}")
async def get_file(request: Request, assessment_id: str, path: str) -> Response:
    _, files = _load(request, assessment_id)
    if path not in BUNDLE_FILES or path not in files:
        raise ApiError(404, "not_found", "Not found.")
    return Response(files[path], media_type=CONTENT_TYPES[path.rsplit(".", 1)[-1]])


@router.post("/api/assessments/{assessment_id}/workspace", status_code=202)
async def create_workspace(request: Request, assessment_id: str) -> Response:
    state = request.app.state
    settings = state.settings
    allowed, retry_after = state.limiter.acquire(client_address(request, settings.trust_proxy))
    if not allowed:
        log_event("rate_limited", retryAfter=retry_after)
        raise ApiError(
            429,
            "rate_limited",
            "Too many uploads from this client; try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    bundle_token = state.store.issue_bundle_token(assessment_id, _owner_token(request))
    if bundle_token is None:
        raise ApiError(404, "not_found", "Not found.")
    ws = state.workspace.create_workspace(assessment_id, bundle_token)
    log_event("workspace_requested")
    return Response(json.dumps(ws.to_dict()), status_code=202, media_type="application/json")


@router.delete("/api/assessments/{assessment_id}")
async def delete_assessment(request: Request, assessment_id: str) -> dict:
    if not request.app.state.store.delete(assessment_id, _owner_token(request)):
        raise ApiError(404, "not_found", "Not found.")
    log_event("assessment_deleted", stored=request.app.state.store.size)
    return {"deleted": True}
