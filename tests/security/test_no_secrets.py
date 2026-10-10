"""No credential-shaped strings in the tree; .env.example has no values; samples use only fictional subscriptions."""

import json
import re
import subprocess
from pathlib import Path

from ..conftest import ROOT, SUB_HUB, SUB_SPOKE

PATTERNS = [
    (re.compile(r"AccountKey=[A-Za-z0-9+/=]{40,}"), "storage account key"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}"), "JWT"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub token"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "API key"),
    (
        re.compile(r"(client_secret|clientSecret|CLIENT_SECRET)\s*[:=]\s*[\"'][A-Za-z0-9~._-]{20,}[\"']"),
        "client secret literal",
    ),
    (re.compile(r"0x4AAAAAAA[A-Za-z0-9_-]{10,}"), "verification site key"),
    (re.compile(r"TURNSTILE_SECRET[ \t]*=[ \t]*[A-Za-z0-9_][^\s#]{7,}"), "verification secret"),
    (re.compile(r'"sharedKey"\s*:\s*"(?!REDACTED)[^"]{8,}"'), "VPN shared key literal"),
]
FICTIONAL = {SUB_HUB, SUB_SPOKE}
GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
SKIP_SUFFIXES = {".png", ".jpg", ".zip", ".ico", ".lock", ".woff", ".woff2"}


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files = [ROOT / line for line in out.splitlines() if line]
    return [
        f
        for f in files
        if f.is_file() and f.suffix not in SKIP_SUFFIXES and ".venv" not in f.parts and "node_modules" not in f.parts
    ]


def test_no_credential_shaped_strings():
    hits = []
    for path in _tracked_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for rx, what in PATTERNS:
            if rx.search(text):
                hits.append(f"{path.relative_to(ROOT)}: {what}")
    assert hits == []


def test_env_example_defines_no_secret_values():
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "TURNSTILE_SECRET=" in env
    for line in env.splitlines():
        if line.startswith("TURNSTILE_SECRET"):
            assert line.strip() == "TURNSTILE_SECRET=", line
    assert not re.search(r"SECRET\s*=[ \t]*\S", env)
    for key in (
        "PORT",
        "NA_ALLOWED_ORIGINS",
        "NA_FRAME_ANCESTORS",
        "NA_SITE_ORIGINS",
        "NA_TURNSTILE_SITE_KEY",
        "NA_PUBLIC_HOST",
        "NA_ALLOW_NO_TURNSTILE",
        "NA_TTL_MINUTES",
        "NA_MAX_ITEMS",
        "NA_RATE_LIMIT_POSTS",
        "NA_RATE_LIMIT_WINDOW_MINUTES",
        "NA_MAX_CONCURRENT",
        "NA_TRUST_PROXY",
        "NA_LOG_SILENT",
        "NA_STATIC_DIR",
        "NA_SAMPLES_DIR",
    ):
        assert re.search(rf"^{key}=", env, re.MULTILINE), key


def test_gitignore_excludes_secrets_and_runtime_data():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for must in (".env", "*.tfstate", "*.tfvars", "data/", ".venv/", "*.pem"):
        assert must in gi, must


def test_samples_are_fictional():
    for path in (ROOT / "samples").glob("*"):
        text = path.read_text(encoding="utf-8")
        guids = set(GUID.findall(text))
        assert guids <= FICTIONAL, f"{path.name}: {guids - FICTIONAL}"
        assert "hcw-sample" in text
    rows = json.loads((ROOT / "samples" / "sample-resource-graph.json").read_text(encoding="utf-8"))["data"]
    assert {r["subscriptionId"] for r in rows} == FICTIONAL
    assert all(
        r["name"].startswith(("hcw-sample-", "hcwsample", "privatelink.", "NetworkWatcher_", "default")) for r in rows
    )
    assert all(r["location"] in ("eastus2", "global") for r in rows)
    public_ips = [r["properties"]["ipAddress"] for r in rows if "ipAddress" in r["properties"]]
    assert public_ips and all(ip.startswith("203.0.113.") for ip in public_ips), "documentation range only"
