import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from network_assessment import __version__
from network_assessment.app import api_routes, create_app
from network_assessment.config import TURNSTILE_ACTION

from ..conftest import SAMPLE_CSV, SAMPLE_PORTAL_CSV, make_settings

JSON = {"content-type": "application/json"}


def test_health_is_flat_and_complete(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert (
        body["ok"] is True
        and body["id"] == "network-assessment"
        and body["version"] == __version__
        and body["edition"] == "lab"
    )
    assert body["azureConnectivity"] == "disabled-by-design" and "addon" not in body
    assert body["turnstile"] == {"required": False, "siteKey": None} and body["siteOrigins"] == [
        "https://hybridcloudworks.com"
    ]
    assert body["rules"] == {"version": "2026.10.0", "count": 45, "liveOnly": 11} and body["model"] == {
        "version": "lab-1.0.0"
    }
    assert body["limits"] == {"maxUploadBytes": 5242880, "maxRows": 5000, "ttlMinutes": 120}
    assert body["capabilities"] == ["resource-graph-export", "report-markdown", "report-json", "bundle-zip", "sample"]
    assert body["asOf"].endswith("Z")
    assert r.headers["x-addon-id"] == "network-assessment" and r.headers["x-addon-version"] == __version__
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cross-origin-opener-policy"] == "same-origin" and r.headers["permissions-policy"]
    assert r.headers["cache-control"] == "no-store" and r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_config_and_rules(client):
    c = client.get("/api/config").json()
    assert c["turnstileAction"] == TURNSTILE_ACTION and c["turnstileRequired"] is False and c["ttlMinutes"] == 120
    assert c["siteOrigins"] == ["https://hybridcloudworks.com"] and c["limits"]["maxRows"] == 5000
    k = client.get("/api/rules").json()
    assert k["count"] == 45 and k["liveOnly"] == 11 and k["version"] == "2026.10.0" and k["verify"] is True
    assert k["rules"][0]["id"] == "AZ-BCDR-001" and k["rules"][-1]["id"] == "AZ-NET-033"
    assert all(r["learnUrl"].startswith("https://learn.microsoft.com/") for r in k["rules"])
    assert {r["appliesTo"] for r in k["rules"]} == {"export", "live-only"}


def test_samples_and_static(client):
    r = client.get("/api/sample.json")
    assert (
        r.status_code == 200
        and r.headers["content-disposition"].endswith('"sample-resource-graph.json"')
        and r.headers["cache-control"] == "no-store"
    )
    assert json.loads(r.content)["count"] == 48
    assert client.get("/api/sample.csv").status_code == 200
    r = client.get("/")
    assert (
        r.status_code == 200
        and "no cloud connectivity by design" in r.text
        and r.headers["cache-control"] == "no-cache"
    )
    assert '<script src="/app.js">' in r.text and "<script>" not in r.text, "no inline scripts"
    assert client.get("/app.js").headers["cache-control"] == "public, max-age=300"
    assert client.get("/theme.css").status_code == 200 and client.get("/styles.css").status_code == 200
    assert client.get("/nope.html").status_code == 404
    assert client.get("/..%2Fpyproject.toml").status_code == 404 and client.get("/../pyproject.toml").status_code == 404
    assert client.get("/web").status_code == 404


def test_api_fallthrough_404_and_405(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json() == {"error": {"code": "not_found", "message": "Not found."}}
    assert (
        client.post("/api/health").status_code == 405
        and client.post("/api/health").json()["error"]["code"] == "method_not_allowed"
    )
    assert client.put("/api/assessments/abc").status_code == 405
    assert client.get("/api/").status_code == 404 and client.get("/api").status_code == 404


def test_create_read_files_delete_lifecycle(client, created):
    assessment_id, headers, body = created
    assert set(body) == {"assessmentId", "ownerToken", "expiresAt", "summary", "ingestionWarnings"}
    assert (
        body["summary"]["resourceCount"] == 48
        and body["expiresAt"].endswith("Z")
        and len(body["ingestionWarnings"]) == 2
    )
    assert (
        body["summary"]["topology"]["pattern"] == "hub_spoke" and body["summary"]["findingsBySeverity"]["critical"] == 3
    )
    r = client.get(f"/api/assessments/{assessment_id}", headers=headers)
    assert r.status_code == 200
    full = r.json()
    assert sorted(full["files"]) == [
        "NOT-FOR-PRODUCTION.md",
        "README.md",
        "bundle.zip",
        "findings.json",
        "report.md",
        "rules.json",
        "summary.json",
        "topology.json",
    ]
    a = full["assessment"]
    assert (
        a["modelVersion"] == "lab-1.0.0"
        and len(a["findings"]) == 45
        and len(a["unknowns"]) == 11
        and len(a["resources"]) == 48
    )
    assert a["findings"][0]["observedState"]["state"] == "observed" and full["expiresAt"] == body["expiresAt"]
    md = client.get(f"/api/assessments/{assessment_id}/report.md", headers=headers)
    assert (
        md.status_code == 200
        and md.headers["content-type"].startswith("text/markdown")
        and "attachment" in md.headers["content-disposition"]
    )
    js = client.get(f"/api/assessments/{assessment_id}/report.json", headers=headers)
    assert js.status_code == 200 and js.json()["id"] == assessment_id and js.json()["rulesVersion"] == "2026.10.0"
    z = client.get(f"/api/assessments/{assessment_id}/bundle.zip", headers=headers)
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    assert sorted(zipfile.ZipFile(io.BytesIO(z.content)).namelist()) == [
        "NOT-FOR-PRODUCTION.md",
        "README.md",
        "findings.json",
        "report.md",
        "rules.json",
        "summary.json",
        "topology.json",
    ]
    f = client.get(f"/api/assessments/{assessment_id}/files/findings.json", headers=headers)
    assert f.status_code == 200 and f.headers["content-type"] == "application/json"
    assert client.get(f"/api/assessments/{assessment_id}/files/bundle.zip", headers=headers).status_code == 404
    assert client.get(f"/api/assessments/{assessment_id}/files/../x", headers=headers).status_code == 404
    assert client.delete(f"/api/assessments/{assessment_id}", headers=headers).json() == {"deleted": True}
    assert client.get(f"/api/assessments/{assessment_id}", headers=headers).status_code == 404
    assert client.delete(f"/api/assessments/{assessment_id}", headers=headers).status_code == 404


def test_owner_token_isolation(client, created):
    assessment_id, headers, _ = created
    assert client.get(f"/api/assessments/{assessment_id}").status_code == 404
    assert client.get(f"/api/assessments/{assessment_id}", headers={"x-owner-token": "wrong"}).status_code == 404
    assert (
        client.get(f"/api/assessments/{assessment_id}/bundle.zip", headers={"x-owner-token": "x" * 200}).status_code
        == 404
    )
    assert client.delete(f"/api/assessments/{assessment_id}", headers={"x-owner-token": "wrong"}).status_code == 404
    assert client.get("/api/assessments/00000000-0000-4000-8000-000000000000", headers=headers).status_code == 404


def test_wrapper_body_csv_body_and_portal_csv(client, sample_rows):
    csv_text = SAMPLE_CSV.read_text(encoding="utf-8")
    r = client.post("/api/assessments", content=csv_text.encode(), headers={"content-type": "text/csv; charset=utf-8"})
    assert r.status_code == 201 and r.json()["summary"]["resourceCount"] == 48
    wrapper = {"format": "arg-csv", "content": csv_text, "fileName": "my export (1).csv"}
    r = client.post("/api/assessments", json=wrapper)
    assert r.status_code == 201 and r.json()["summary"]["findingsCount"] == 45
    r = client.post("/api/assessments", json={"format": "arg-json", "content": json.dumps(sample_rows[:3])})
    assert r.status_code == 201 and r.json()["summary"]["resourceCount"] == 3
    r = client.post(
        "/api/assessments", json={"count": 1, "data": sample_rows[:1], "skip_token": "x", "total_records": 9}
    )
    assert r.status_code == 201 and r.json()["ingestionWarnings"][0].startswith("export is paged")
    portal = SAMPLE_PORTAL_CSV.read_text(encoding="utf-8")
    r = client.post("/api/assessments", content=portal.encode(), headers={"content-type": "text/csv"})
    assert r.status_code == 201, "the portal All-resources CSV is accepted with a warning"
    body = r.json()
    assert body["ingestionWarnings"][0].startswith("no properties column")
    assert body["summary"]["unknownRules"] > 11 and body["summary"]["findingsCount"] >= 1


@pytest.mark.parametrize(
    "content,headers,status,code",
    [
        (b"[{", JSON, 400, "invalid_json"),
        (b'{"format": "xml", "content": "x"}', JSON, 400, "invalid_request"),
        (b'{"format": "arg-json", "content": "[]", "fileName": "../x.json"}', JSON, 400, "invalid_request"),
        (b'{"format": "arg-json", "content": "[]", "extra": 1}', JSON, 400, "invalid_request"),
        (b'{"nope": 1}', JSON, 400, "invalid_export"),
        (b"[]", JSON, 400, "invalid_export"),
        (b'[{"name": "x"}]', JSON, 400, "invalid_export"),
        (b"name,location\nx,y\n", {"content-type": "text/csv"}, 400, "invalid_export"),
        (b'[{"type": "microsoft.compute/virtualmachines", "name": "vm"}]', JSON, 422, "ingestion_failed"),
        (b"<xml/>", {"content-type": "application/xml"}, 415, "unsupported_media_type"),
        (b"x", {}, 415, "unsupported_media_type"),
    ],
)
def test_upload_errors(client, content, headers, status, code):
    r = client.post("/api/assessments", content=content, headers=headers)
    assert r.status_code == status, r.text
    body = r.json()
    assert body["error"]["code"] == code and body["error"]["message"]
    if "details" in body["error"]:
        assert "hcw-sample" not in json.dumps(body["error"]["details"])


def test_invalid_request_details_name_fields_not_content(client):
    r = client.post("/api/assessments", json={"format": "arg-json", "content": ""})
    assert r.status_code == 400 and r.json()["error"]["details"] == {"fields": ["content"]}


def test_too_many_rows(settings):
    app = create_app(make_settings(max_rows=2), sweep=False)
    with TestClient(app) as c:
        rows = [{"name": f"n{i}", "type": "microsoft.network/virtualnetworks"} for i in range(3)]
        r = c.post("/api/assessments", json=rows)
        assert r.status_code == 422 and r.json()["error"] == {
            "code": "too_many_rows",
            "message": "The export has more rows than the limit.",
            "details": {"rows": 3, "maxRows": 2},
        }


def test_413_declared_and_streamed(sample_json_bytes):
    app = create_app(make_settings(max_upload_bytes=1000), sweep=False)
    with TestClient(app) as c:
        r = c.post("/api/assessments", content=sample_json_bytes, headers=JSON)
        assert r.status_code == 413 and r.json()["error"]["code"] == "too_large"

        def chunks():
            for _ in range(20):
                yield b"[" + b" " * 100

        r = c.post("/api/assessments", content=chunks(), headers=JSON | {"transfer-encoding": "chunked"})
        assert r.status_code == 413


def test_rate_limit_429_with_retry_after(sample_rows):
    app = create_app(make_settings(rate_limit_posts=2, rate_limit_window_minutes=10), sweep=False)
    with TestClient(app) as c:
        for _ in range(2):
            assert c.post("/api/assessments", json=sample_rows[:1]).status_code == 201
        r = c.post("/api/assessments", json=sample_rows[:1])
        assert (
            r.status_code == 429 and r.json()["error"]["code"] == "rate_limited" and int(r.headers["retry-after"]) >= 1
        )
        r = c.post("/api/assessments", json=sample_rows[:1], headers={"x-forwarded-for": "203.0.113.9"})
        assert r.status_code == 429, "X-Forwarded-For is ignored unless NA_TRUST_PROXY=1"
    app = create_app(make_settings(rate_limit_posts=1, rate_limit_window_minutes=10, trust_proxy=True), sweep=False)
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/assessments", json=sample_rows[:1], headers={"x-forwarded-for": "203.0.113.1, 10.0.0.1"}
            ).status_code
            == 201
        )
        assert (
            c.post("/api/assessments", json=sample_rows[:1], headers={"x-forwarded-for": "203.0.113.1"}).status_code
            == 429
        )
        assert (
            c.post("/api/assessments", json=sample_rows[:1], headers={"x-forwarded-for": "203.0.113.2"}).status_code
            == 201
        )


def test_503_overloaded_when_concurrency_bound_is_held(sample_rows):
    app = create_app(make_settings(max_concurrent=1), sweep=False)
    app.state.bound.wait_seconds = 0.05
    with TestClient(app) as c:
        import asyncio

        asyncio.run(app.state.bound.acquire())
        r = c.post("/api/assessments", json=sample_rows[:1])
        assert r.status_code == 503 and r.json()["error"]["code"] == "overloaded" and r.headers["retry-after"] == "2"
        app.state.bound.release()
        assert c.post("/api/assessments", json=sample_rows[:1]).status_code == 201


def test_turnstile_fail_closed_without_secret(sample_rows):
    app = create_app(make_settings(allow_no_turnstile=False), sweep=False)
    with TestClient(app) as c:
        health = c.get("/api/health").json()
        assert health["turnstile"] == {"required": True, "siteKey": None}
        r = c.post("/api/assessments", json=sample_rows[:1])
        assert r.status_code == 503 and r.json()["error"]["code"] == "turnstile_not_configured"


def test_turnstile_enforced_with_mocked_siteverify(sample_rows):
    calls = []

    def opener(request, timeout):
        form = dict(p.split("=") for p in request.data.decode().split("&"))
        calls.append(form)
        host = "network-assessment.lab.hybridcloudworks.com"
        if form["response"] == "good":
            return json.dumps({"success": True, "action": TURNSTILE_ACTION, "hostname": host}).encode()
        if form["response"] == "wrong-action":
            return json.dumps({"success": True, "action": "login", "hostname": host}).encode()
        if form["response"] == "wrong-host":
            return json.dumps({"success": True, "action": TURNSTILE_ACTION, "hostname": "evil.example"}).encode()
        return json.dumps({"success": False, "error-codes": ["invalid-input-response"]}).encode()

    app = create_app(
        make_settings(
            turnstile_secret="secret-value",
            turnstile_site_key="1x00000000000000000000AA",
            public_host="network-assessment.lab.hybridcloudworks.com",
            allow_no_turnstile=True,
        ),
        verifier=opener,
        sweep=False,
    )
    with TestClient(app) as c:
        health = c.get("/api/health").json()
        assert health["turnstile"] == {"required": True, "siteKey": "1x00000000000000000000AA"}
        assert "https://challenges.cloudflare.com" in c.get("/").headers["content-security-policy"]
        r = c.post("/api/assessments", json=sample_rows[:1])
        assert r.status_code == 403 and r.json()["error"]["details"] == {"codes": ["missing-input-response"]}
        r = c.post("/api/assessments", json=sample_rows[:1], headers={"x-turnstile-token": "bad"})
        assert r.status_code == 403 and r.json()["error"]["details"] == {"codes": ["invalid-input-response"]}
        r = c.post("/api/assessments", json=sample_rows[:1], headers={"x-turnstile-token": "wrong-action"})
        assert r.status_code == 403 and r.json()["error"]["details"] == {"codes": ["action-mismatch"]}
        r = c.post("/api/assessments", json=sample_rows[:1], headers={"x-turnstile-token": "wrong-host"})
        assert r.status_code == 403 and r.json()["error"]["details"] == {"codes": ["hostname-mismatch"]}
        r = c.post("/api/assessments", json=sample_rows[:1], headers={"x-turnstile-token": "good"})
        assert r.status_code == 201
        assert calls[-1]["secret"] == "secret-value" and calls[-1]["remoteip"] == "testclient"


def test_cors_exact_origin():
    app = create_app(make_settings(allowed_origins=("https://hybridcloudworks.com",)), sweep=False)
    with TestClient(app) as c:
        pre = c.options(
            "/api/assessments",
            headers={"origin": "https://hybridcloudworks.com", "access-control-request-method": "POST"},
        )
        assert pre.status_code == 204 and pre.headers["access-control-allow-origin"] == "https://hybridcloudworks.com"
        assert (
            "x-turnstile-token" in pre.headers["access-control-allow-headers"]
            and pre.headers["access-control-max-age"] == "600"
        )
        bad = c.options(
            "/api/assessments", headers={"origin": "https://evil.example", "access-control-request-method": "POST"}
        )
        assert bad.status_code == 403 and bad.json()["error"]["code"] == "forbidden"
        sub = c.options(
            "/api/assessments",
            headers={"origin": "https://hybridcloudworks.com.evil.example", "access-control-request-method": "POST"},
        )
        assert sub.status_code == 403
        r = c.get("/api/health", headers={"origin": "https://hybridcloudworks.com"})
        assert (
            r.headers["access-control-allow-origin"] == "https://hybridcloudworks.com"
            and "content-disposition" in r.headers["access-control-expose-headers"]
        )
        r = c.get("/api/health", headers={"origin": "https://evil.example"})
        assert "access-control-allow-origin" not in r.headers
        r = c.get("/api/health")
        assert "access-control-allow-origin" not in r.headers


def test_cors_closed_when_no_origins_configured(client):
    pre = client.options(
        "/api/assessments", headers={"origin": "https://hybridcloudworks.com", "access-control-request-method": "POST"}
    )
    assert pre.status_code == 403


def test_frame_ancestors_configurable():
    app = create_app(
        make_settings(frame_ancestors="https://hybridcloudworks.com https://www.hybridcloudworks.com"), sweep=False
    )
    with TestClient(app) as c:
        r = c.get("/")
        assert (
            "frame-ancestors https://hybridcloudworks.com https://www.hybridcloudworks.com"
            in r.headers["content-security-policy"]
        )
        assert "x-frame-options" not in r.headers


def test_unhandled_error_is_enveloped_and_logged(client, monkeypatch):
    from network_assessment.routes import health as health_module

    def boom(request):
        raise RuntimeError("sub /subscriptions/00000000-0000-0000-0000-000000000001/x")

    monkeypatch.setattr(health_module, "health_body", boom)
    client_no_raise = TestClient(client.app, raise_server_exceptions=False)
    r = client_no_raise.get("/api/health")
    assert r.status_code == 500 and r.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong on our side."}
    }


def test_api_routes_table(client):
    table = api_routes(client.app)
    assert table["/api/assessments"] == {"POST"} and table["/api/assessments/{assessment_id}"] == {"GET", "DELETE"}
    assert "/api/{rest:path}" not in table and table["/api/rules"] == {"GET"}


def test_lifespan_sweeper_runs(sample_rows, monkeypatch):
    import asyncio
    import time

    from network_assessment import app as app_module

    monkeypatch.setattr(app_module, "SWEEP_SECONDS", 0.01)
    app = create_app(make_settings(ttl_minutes=1), sweep=True)
    with TestClient(app) as c:
        assert c.post("/api/assessments", json=sample_rows[:1]).status_code == 201
        app.state.store._items[next(iter(app.state.store._items))].expires_at = 0
        asyncio.run(asyncio.sleep(0))
        deadline = time.time() + 2
        while app.state.store.size and time.time() < deadline:
            time.sleep(0.02)
        assert app.state.store.size == 0
