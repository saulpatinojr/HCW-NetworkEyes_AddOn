from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from network_assessment import engine
from network_assessment.app import create_app
from network_assessment.config import Settings

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = ROOT / "samples" / "sample-resource-graph.json"
SAMPLE_CSV = ROOT / "samples" / "sample-resource-graph.csv"
SAMPLE_PORTAL_CSV = ROOT / "samples" / "sample-all-resources-export.csv"
SUB_HUB = "00000000-0000-0000-0000-000000000001"
SUB_SPOKE = "00000000-0000-0000-0000-000000000002"

# The topology model marker each engine must report (a shared contract, ADR-0004). The interim port declares
# `lab-1.0.0` (equivalent to the App's 1.3.0 Azure subset); the wheel reports its own model version. A new engine
# release that is not in this table fails tests/unit/test_engine.py, which is the "needs adaptation" signal.
MODEL_VERSIONS = {engine.PORT_SOURCE: "lab-1.0.0", "cna-azure-network-engine 0.1.0": "1.4.0"}
EXPECTED_MODEL_VERSION = MODEL_VERSIONS.get(engine.SOURCE)


def make_settings(**overrides) -> Settings:
    base = {"allow_no_turnstile": True, "log_silent": True, "site_origins": ("https://hybridcloudworks.com",)}
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def client(settings):
    app = create_app(settings, sweep=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_json_bytes() -> bytes:
    return SAMPLE_JSON.read_bytes()


@pytest.fixture
def sample_rows() -> list[dict]:
    return json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))["data"]


@pytest.fixture
def created(client, sample_json_bytes):
    r = client.post("/api/assessments", content=sample_json_bytes, headers={"content-type": "application/json"})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["assessmentId"], {"x-owner-token": body["ownerToken"]}, body


@pytest.fixture
def anyio_backend():
    return "asyncio"
