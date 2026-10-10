import io
import json
import sys
import urllib.error

import pytest

from network_assessment.config import Settings
from network_assessment.security import logging as logs
from network_assessment.security.headers import cache_control_for, content_security_policy, security_headers
from network_assessment.security.ratelimit import MAX_TRACKED_CLIENTS, ConcurrencyBound, TokenBucketLimiter
from network_assessment.security.redaction import VisitorDataError, scrub
from network_assessment.security.turnstile import SITEVERIFY_URL, Verdict, verify


def _opener(payload, *, raise_exc=None, capture=None):
    def opener(request, timeout):
        assert request.full_url == SITEVERIFY_URL and timeout == 5.0
        if capture is not None:
            capture.append(request.data.decode())
        if raise_exc:
            raise raise_exc
        return json.dumps(payload).encode() if not isinstance(payload, bytes) else payload

    return opener


def test_turnstile_verdicts():
    assert verify("s", None, "1.2.3.4") == Verdict(False, ["missing-input-response"])
    assert verify("s", "x" * 3000, None).codes == ["missing-input-response"]
    sent = []
    ok = {
        "success": True,
        "action": "network-assessment-upload",
        "hostname": "network-assessment.lab.hybridcloudworks.com",
    }
    assert verify("s", "tok", "1.2.3.4", opener=_opener(ok, capture=sent)).ok
    assert "remoteip=1.2.3.4" in sent[0] and "secret=s" in sent[0] and "response=tok" in sent[0]
    assert verify(
        "s", "tok", None, expected_hostname="network-assessment.lab.hybridcloudworks.com", opener=_opener(ok)
    ).ok
    assert verify("s", "tok", None, expected_hostname="other.example", opener=_opener(ok)).codes == [
        "hostname-mismatch"
    ]
    assert verify("s", "tok", None, opener=_opener({"success": True, "action": "other"})).codes == ["action-mismatch"]
    assert verify(
        "s", "tok", None, opener=_opener({"success": False, "error-codes": ["timeout-or-duplicate", 5]})
    ).codes == ["timeout-or-duplicate"]
    assert verify("s", "tok", None, opener=_opener({"success": False})).codes == ["invalid-input-response"]
    assert verify("s", "tok", None, opener=_opener(b"not json")).codes == ["verification-unavailable"]
    assert verify("s", "tok", None, opener=_opener([1])).codes == ["verification-unavailable"]
    assert verify("s", "tok", None, opener=_opener({}, raise_exc=urllib.error.URLError("x"))).codes == [
        "verification-unavailable"
    ]
    assert verify("s", "tok", None, opener=_opener({}, raise_exc=TimeoutError())).codes == ["verification-unavailable"]


def test_csp_and_headers_follow_settings():
    plain = Settings()
    csp = content_security_policy(plain)
    assert (
        "frame-ancestors 'none'" in csp
        and "challenges.cloudflare.com" not in csp
        and "base-uri 'none'" in csp
        and "form-action 'self'" in csp
    )
    headers = dict(security_headers(plain))
    assert (
        headers[b"x-frame-options"] == b"DENY"
        and headers[b"x-addon-id"] == b"network-assessment"
        and headers[b"x-content-type-options"] == b"nosniff"
    )
    assert (
        headers[b"referrer-policy"] == b"no-referrer"
        and headers[b"permissions-policy"] == b"camera=(), microphone=(), geolocation=()"
        and headers[b"cross-origin-opener-policy"] == b"same-origin"
    )
    framed = Settings(
        frame_ancestors="https://hybridcloudworks.com https://www.hybridcloudworks.com", turnstile_site_key="k"
    )
    csp = content_security_policy(framed)
    assert "frame-ancestors https://hybridcloudworks.com https://www.hybridcloudworks.com" in csp
    assert (
        "script-src 'self' https://challenges.cloudflare.com" in csp
        and "frame-src https://challenges.cloudflare.com" in csp
    )
    assert b"x-frame-options" not in dict(security_headers(framed))
    assert (
        cache_control_for("/api/health") == b"no-store"
        and cache_control_for("/") == b"no-cache"
        and cache_control_for("/app.js") == b"public, max-age=300"
    )


def test_token_bucket_refills_and_prunes():
    now = [0.0]
    limiter = TokenBucketLimiter(2, 10.0, clock=lambda: now[0])
    assert limiter.acquire("a") == (True, 0) and limiter.acquire("a") == (True, 0)
    allowed, retry = limiter.acquire("a")
    assert not allowed and retry >= 1
    assert limiter.acquire("b") == (True, 0), "clients are independent"
    now[0] += 5.0
    assert limiter.acquire("a") == (True, 0)
    limiter._buckets.clear()
    for i in range(MAX_TRACKED_CLIENTS):
        limiter.acquire(f"c{i}")
    now[0] += 100.0
    assert limiter.acquire("new") == (True, 0)
    assert len(limiter._buckets) < MAX_TRACKED_CLIENTS


def test_token_bucket_prune_clears_when_everyone_is_active():
    now = [0.0]
    limiter = TokenBucketLimiter(1, 1000.0, clock=lambda: now[0])
    for i in range(MAX_TRACKED_CLIENTS):
        limiter.acquire(f"c{i}")
    assert limiter.acquire("new") == (True, 0)
    assert len(limiter._buckets) == 1


@pytest.mark.anyio
async def test_concurrency_bound_times_out():
    bound = ConcurrencyBound(1, wait_seconds=0.05)
    assert await bound.acquire()
    assert not await bound.acquire()
    bound.release()
    assert await bound.acquire()
    bound.release()


def test_logging_writer_is_guarded(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    logs.configure(silent=False)
    logs.log_event("startup", n=1, flag=True)
    with pytest.raises(VisitorDataError):
        logs.log_event("startup", name="hcw-sample-vnet-hub")
    with pytest.raises(VisitorDataError):
        logs.log_event("startup", **{"not an identifier": 1})
    logs.log_exception("unhandled_error", RuntimeError("sub /subscriptions/00000000-0000-0000-0000-000000000001/x"))
    out = buf.getvalue()
    assert '"event":"startup"' in out and "00000000-0000" not in out and "<redacted>" in out
    logs.configure(silent=True)
    logs.log_event("startup")
    assert out == buf.getvalue()


def test_scrub_shapes():
    assert scrub("AccountKey=" + "A" * 40) == "AccountKey=<redacted>".replace("AccountKey=<redacted>", "<redacted>")
    assert scrub("ghp_" + "a" * 30 + " and 11111111-2222-3333-4444-555555555555") == "<redacted> and <redacted>"
    assert len(scrub("x" * 1000)) == 500
