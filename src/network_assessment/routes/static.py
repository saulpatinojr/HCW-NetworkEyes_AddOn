"""The samples and the pane's static files. Paths are normalised and must stay under the configured directory."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse

from network_assessment.errors import ApiError

router = APIRouter()

MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".csv": "text/csv; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}


def safe_file(base: Path, relative: str) -> Path | None:
    root = base.resolve()
    try:
        candidate = (root / relative).resolve()
    except OSError:
        return None
    if candidate == root or root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def _sample(request: Request, name: str) -> Response:
    path = safe_file(request.app.state.settings.samples_dir, name)
    if path is None:
        raise ApiError(404, "not_found", "Not found.")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[path.suffix],
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )


@router.get("/api/sample.json")
async def sample_json(request: Request) -> Response:
    return _sample(request, "sample-resource-graph.json")


@router.get("/api/sample.csv")
async def sample_csv(request: Request) -> Response:
    return _sample(request, "sample-resource-graph.csv")


pane = APIRouter()


@pane.get("/{path:path}", include_in_schema=False)
async def static_file(request: Request, path: str) -> Response:
    if path.startswith("api/") or path == "api":
        raise ApiError(404, "not_found", "Not found.")
    relative = path or "index.html"
    file = safe_file(request.app.state.settings.static_dir, relative)
    if file is None:
        raise ApiError(404, "not_found", "Not found.")
    return FileResponse(file, media_type=MEDIA_TYPES.get(file.suffix, "application/octet-stream"))
