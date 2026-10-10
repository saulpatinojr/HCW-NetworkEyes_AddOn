"""Logs carry counts, durations, flags and allowed words only; never ids, names, tokens or cell content."""

import io
import json
import sys

from fastapi.testclient import TestClient

from network_assessment.app import create_app
from network_assessment.security import logging as logs
from network_assessment.security.redaction import ALLOWED_WORDS

from ..conftest import make_settings


def test_lifecycle_logs_are_content_free(sample_json_bytes, monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    app = create_app(make_settings(log_silent=False), sweep=False)
    with TestClient(app) as c:
        r = c.post("/api/assessments", content=sample_json_bytes, headers={"content-type": "application/json"})
        body = r.json()
        headers = {"x-owner-token": body["ownerToken"]}
        c.get(f"/api/assessments/{body['assessmentId']}", headers=headers)
        c.post("/api/assessments", content=b"[{", headers={"content-type": "application/json"})
        c.post("/api/assessments", content=b'{"x":1}', headers={"content-type": "application/json"})
        c.delete(f"/api/assessments/{body['assessmentId']}", headers=headers)
    lines = [json.loads(line) for line in buf.getvalue().splitlines()]
    events = [line["event"] for line in lines]
    assert (
        events[0] == "startup"
        and "assessment_created" in events
        and "assessment_read" in events
        and "assessment_rejected" in events
        and "assessment_deleted" in events
        and events[-1] == "shutdown"
    )
    text = buf.getvalue()
    assert body["assessmentId"] not in text and body["ownerToken"] not in text
    assert "hcw-sample" not in text and "00000000-0000" not in text and "eastus2" not in text and "10.0." not in text
    for line in lines:
        for key, value in line.items():
            if key in ("ts",):
                continue
            assert value is None or isinstance(value, bool | int | float) or value in ALLOWED_WORDS, (key, value)
    logs.configure(silent=True)


def test_turnstile_disabled_warning_is_logged_at_startup(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    app = create_app(make_settings(log_silent=False, allow_no_turnstile=True), sweep=False)
    with TestClient(app):
        pass
    assert any(
        json.loads(line) == {**json.loads(line), "event": "turnstile_disabled", "warning": True}
        for line in buf.getvalue().splitlines()
    )
    logs.configure(silent=True)
