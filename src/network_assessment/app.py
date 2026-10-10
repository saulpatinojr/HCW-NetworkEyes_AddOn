"""The application factory. Importing this module runs the edition guard: a lab that could reach Azure never starts."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from network_assessment import __version__
from network_assessment.config import Settings
from network_assessment.edition import assert_lab_cannot_reach_azure
from network_assessment.errors import DEFAULT_CODES, DEFAULT_MESSAGES, ApiError
from network_assessment.routes import assessments, config, health, rules, static
from network_assessment.rules.registry import RULES
from network_assessment.security import logging as logs
from network_assessment.security.cors import ExactOriginCorsMiddleware
from network_assessment.security.headers import SecurityHeadersMiddleware
from network_assessment.security.ratelimit import ConcurrencyBound, TokenBucketLimiter
from network_assessment.store import AssessmentStore

assert_lab_cannot_reach_azure()

SWEEP_SECONDS = 60


def _envelope(status: int, code: str, message: str, details=None, headers=None) -> JSONResponse:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status, headers=headers or {})


def create_app(settings: Settings | None = None, *, verifier=None, sweep: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    logs.configure(silent=settings.log_silent)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logs.log_event("startup", rules=len(RULES), turnstileRequired=settings.turnstile_required)
        if not settings.turnstile_required and settings.allow_no_turnstile:
            logs.log_event("turnstile_disabled", warning=True)
        task = asyncio.create_task(_sweeper(app)) if sweep else None
        try:
            yield
        finally:
            if task:
                task.cancel()
            logs.log_event("shutdown", stored=app.state.store.size)

    app = FastAPI(
        title="Network Assessment (lab edition)",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.store = AssessmentStore(settings.ttl_minutes * 60, settings.max_items)
    app.state.limiter = TokenBucketLimiter(settings.rate_limit_posts, settings.rate_limit_window_minutes * 60)
    app.state.bound = ConcurrencyBound(settings.max_concurrent)
    app.state.verifier = verifier

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return _envelope(exc.status, exc.code, exc.message, exc.details, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return _envelope(400, "invalid_request", DEFAULT_MESSAGES[400])

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        status = exc.status_code
        return _envelope(
            status,
            DEFAULT_CODES.get(status, "error"),
            DEFAULT_MESSAGES.get(status, "The request failed."),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logs.log_exception("unhandled_error", exc)
        return _envelope(500, "internal_error", DEFAULT_MESSAGES[500])

    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(rules.router)
    app.include_router(static.router)
    app.include_router(assessments.router)

    @app.api_route(
        "/api/{rest:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        include_in_schema=False,
    )
    async def _api_fallthrough(request: Request, rest: str):
        for route in iter_routes(app):
            if route.path.startswith("/api/{rest") or route.path == "/{path:path}":
                continue
            if route.path_regex.match(request.url.path):
                raise ApiError(405, "method_not_allowed", DEFAULT_MESSAGES[405])
        raise ApiError(404, "not_found", "Not found.")

    app.include_router(static.pane)

    app.add_middleware(ExactOriginCorsMiddleware, allowed_origins=settings.allowed_origins)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    return app


def iter_routes(app_or_router):
    """Every concrete route, descending through included routers (FastAPI nests them under app.routes)."""
    for route in getattr(app_or_router, "routes", []):
        if getattr(route, "path_regex", None) is not None and getattr(route, "methods", None):
            yield route
        else:
            yield from iter_routes(getattr(route, "original_router", route))


def api_routes(app: FastAPI) -> dict[str, set[str]]:
    """{path: methods} for the documented /api surface (the catch-all and the pane route excluded)."""
    table: dict[str, set[str]] = {}
    for route in iter_routes(app):
        if not route.path.startswith("/api/") or route.path.startswith("/api/{rest"):
            continue
        table.setdefault(route.path, set()).update(m for m in route.methods if m not in ("HEAD", "OPTIONS"))
    return table


async def _sweeper(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(SWEEP_SECONDS)
        removed = app.state.store.sweep()
        if removed:
            logs.log_event("sweep", removed=removed, stored=app.state.store.size)
