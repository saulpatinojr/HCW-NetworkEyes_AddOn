"""docs/api/openapi.yaml and the implementation agree two-way: every documented path+method exists and vice versa."""

import re
from pathlib import Path

from network_assessment.app import api_routes, create_app

from ..conftest import ROOT, make_settings

SPEC = Path(ROOT / "docs" / "api" / "openapi.yaml").read_text(encoding="utf-8")


def _spec_routes() -> dict[str, set[str]]:
    routes: dict[str, set[str]] = {}
    current = None
    for line in SPEC.splitlines():
        m = re.match(r"^  (/api/\S+):\s*$", line)
        if m:
            current = m.group(1)
            routes[current] = set()
            continue
        m = re.match(r"^    (get|post|put|patch|delete):\s*$", line)
        if m and current:
            routes[current].add(m.group(1).upper())
    return routes


def _normalise(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_openapi_paths_and_methods_match_app_both_ways():
    spec = {_normalise(p): m for p, m in _spec_routes().items()}
    app = {_normalise(p): m for p, m in api_routes(create_app(make_settings(), sweep=False)).items()}
    assert spec, "spec parsed no paths"
    assert set(spec) == set(app), f"spec-only: {set(spec) - set(app)}; app-only: {set(app) - set(spec)}"
    for path in spec:
        assert spec[path] == app[path], f"{path}: spec {spec[path]} vs app {app[path]}"


def test_spec_documents_every_error_code_the_api_emits():
    src = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "network_assessment").rglob("*.py"))
    for code in sorted(set(re.findall(r'ApiError\(\s*\d{3},\s*"([a-z_]+)"', src)) - {"forbidden"}):
        assert code in SPEC, f"error code {code} is not documented"
    for code in ("turnstile_not_configured", "not_found", "rate_limited", "overloaded", "invalid_export"):
        assert code in SPEC


def test_spec_health_matches_the_standard():
    assert "id: { const: network-assessment }" in SPEC and "edition: { const: lab }" in SPEC
    assert (
        "azureConnectivity: { const: disabled-by-design }" in SPEC
        and "turnstileAction: { const: network-assessment-upload }" in SPEC
    )
