"""The lab edition is technically unable to reach Azure (AddOn Integration Standard, section 19)."""

import ast
import re
import subprocess
import sys
import tomllib

import pytest

from ..conftest import ROOT

FORBIDDEN_ENDPOINTS = ("management.azure.com", "login.microsoftonline.com", "graph.microsoft.com")
FORBIDDEN_MODULES = ("azure", "msal", "boto3", "botocore", "msrest")
FORBIDDEN_SYMBOLS = ("azure.identity", "DefaultAzureCredential", "ClientSecretCredential", "import boto3")
PY_DIRS = [ROOT / "src", ROOT / "scripts"]


def _py_files():
    for base in PY_DIRS:
        yield from (p for p in base.rglob("*.py") if ".venv" not in p.parts)


CLOUD_SDK_PREFIXES = ("azure-", "msal", "msrest", "boto3", "botocore")


def _is_cloud_sdk(name: str) -> bool:
    return name.lower().replace("_", "-").startswith(CLOUD_SDK_PREFIXES)


def test_no_cloud_sdk_in_dependency_manifests():
    for name in ("pyproject.toml", "uv.lock"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for pkg in CLOUD_SDK_PREFIXES:
            assert not re.search(rf"^{pkg}[\w-]*==", text, re.MULTILINE), f"{name} pins {pkg}"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requested = list(project["project"]["dependencies"])
    for group in project.get("dependency-groups", {}).values():
        requested += [d for d in group if isinstance(d, str)]
    for dep in requested:
        name = re.split(r"[\s\[<>=!~;@]", dep, maxsplit=1)[0]
        assert not _is_cloud_sdk(name), f"pyproject.toml depends on {name}"
        # No extra of any dependency: the engine wheel's [azure] extra is its live discovery.
        assert "[" not in dep.split("@", 1)[0], f"pyproject.toml asks for an extra: {dep}"
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    for package in lock["package"]:
        # Everything uv can install is a [[package]] entry.
        assert not _is_cloud_sdk(package["name"]), f"uv.lock locks {package['name']}"
        for table in ("dependencies", "optional-dependencies", "dev-dependencies"):
            entries = package.get(table, [])
            entries = [e for v in entries.values() for e in v] if isinstance(entries, dict) else entries
            for entry in entries:
                assert not _is_cloud_sdk(entry["name"]), f"uv.lock: {package['name']} pulls in {entry['name']}"
        # A dependency's own metadata may name cloud SDKs only behind an extra (the engine wheel's [azure] live
        # discovery), and the checks above prove no extra is requested and nothing of it is locked.
        for req in package.get("metadata", {}).get("requires-dist", []):
            if _is_cloud_sdk(req["name"]):
                assert "extra ==" in req.get("marker", ""), f"uv.lock: {package['name']} requires {req['name']}"


def test_no_cloud_sdk_imports_anywhere():
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] not in FORBIDDEN_MODULES, f"{path} imports {name}"


def test_no_azure_endpoints_or_credential_symbols_in_code_or_pane():
    for base in [ROOT / "src", ROOT / "web", ROOT / "scripts"]:
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".js", ".html", ".css", ".json"} and ".venv" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for endpoint in FORBIDDEN_ENDPOINTS:
                    assert endpoint not in text, f"{path} references {endpoint}"
                for symbol in FORBIDDEN_SYMBOLS:
                    assert symbol not in text, f"{path} references {symbol}"


def test_guard_refuses_identity_endpoint_in_a_fresh_process():
    proc = subprocess.run(
        [sys.executable, "-c", "import network_assessment.app"],
        env={
            "PATH": "/usr/bin:/bin",
            "IDENTITY_ENDPOINT": "http://169.254.169.254/metadata/identity",
            "PYTHONPATH": ":".join(sys.path),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode != 0


def test_cloud_sdks_not_importable_in_this_environment():
    for module in ("azure", "msal", "boto3"):
        with pytest.raises(ImportError):
            __import__(module)


def test_pane_has_no_credential_inputs():
    for path in (ROOT / "web").glob("*"):
        text = path.read_text(encoding="utf-8")
        assert 'type="password"' not in text and "type='password'" not in text, path
        assert "<input" not in text or 'type="file"' in text, "the only input is the file picker"
    assert "never asks for credentials" in (ROOT / "web" / "index.html").read_text(encoding="utf-8")


def test_dockerfile_and_compose_have_no_azure():
    """Outside comments, the only `azure` in the Dockerfile is the boundary guard's forbidden list."""
    for name in ("infrastructure/docker/Dockerfile", "docker-compose.yml"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            code = line.split("#", 1)[0].lower()
            if "azure" in code or "msal" in code or "boto3" in code:
                assert "forbidden" in code or "edition boundary" in code, f"{name}: {line.strip()}"
            assert "pip install" not in code or "requirements.lock.txt" in code, f"{name}: {line.strip()}"
            assert "identity_endpoint=" not in code and "msi_endpoint=" not in code, f"{name}: {line.strip()}"
            assert "network_mode" not in code and "/var/opt/azcmagent" not in code, f"{name}: {line.strip()}"


def test_health_reports_disabled_by_design(client):
    assert client.get("/api/health").json()["azureConnectivity"] == "disabled-by-design"


def test_coder_template_enforces_adr0032_sandbox_boundary():
    """The na-guided-lab Coder template enforces ADR-0032 / LAB-5 sandbox hardening."""
    tf = (ROOT / "infrastructure" / "coder" / "template" / "main.tf").read_text(encoding="utf-8")
    code_lines = [line.split("#", 1)[0] for line in tf.splitlines()]
    code = "\n".join(code_lines)
    assert 'host = "tcp://coder-docker-proxy:2375"' in code
    assert 'uid            = "65534:65534"' in code
    assert 'home           = "/tmp/home"' in code
    assert 'assessment_dir = "/tmp/home/assessment"' in code
    assert "subdomain       = true" in code
    assert "subdomain = false" not in code
    assert "privileged    = false" in code
    assert 'security_opts = ["no-new-privileges:true"]' in code
    assert 'drop = ["ALL"]' in code
    assert "host_path" not in code
    assert "docker.sock" not in code
    assert "/usr/local/libexec/hcw-boot/hcw-boot network-assessment" in code
    assert "python3 -m zipfile -e" in code
