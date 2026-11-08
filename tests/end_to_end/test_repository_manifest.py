"""repository.manifest.json lists real files and the packaging scripts honour its excludes."""

import json

from ..conftest import ROOT


def test_manifest_required_files_exist_and_excludes_are_honoured():
    manifest = json.loads((ROOT / "repository.manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "hcw-networkeyes-addon" and manifest["archive"].endswith(".zip")
    missing = [f for f in manifest["requiredFiles"] if not (ROOT / f).is_file()]
    assert missing == []
    for must in (".venv", ".git", "__pycache__", ".env", "*.zip"):
        assert any(must in e for e in manifest["packageExcludes"]), must
    sh = (ROOT / "scripts" / "package-repository.sh").read_text(encoding="utf-8")
    ps = (ROOT / "scripts" / "package-repository.ps1").read_text(encoding="utf-8")
    for exclude in manifest["packageExcludes"]:
        token = exclude.rstrip("/").lstrip("*")
        assert token in sh, f"package-repository.sh does not exclude {exclude}"
        assert token.replace(".", "\\.") in ps or token in ps, f"package-repository.ps1 does not exclude {exclude}"


def test_manifest_version_matches_pyproject():
    manifest = json.loads((ROOT / "repository.manifest.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{manifest["version"]}"' in pyproject
    from network_assessment import __version__

    assert __version__ == manifest["version"]


def test_the_interim_port_stays_deleted():
    """The engine is the wheel only (ADR-0006): the ported packages, PROVENANCE.md and the lab's own normalizer are
    gone, and no source, test or script imports them again."""
    pkg = ROOT / "src" / "network_assessment"
    for gone in ("model", "rules", "classify"):
        assert not (pkg / gone).exists(), f"src/network_assessment/{gone} is back; engine changes go upstream"
    assert not (pkg / "ingestion" / "normalize.py").exists()
    assert not (ROOT / "PROVENANCE.md").exists()
    banned = tuple(f"network_assessment.{m}" for m in ("model", "rules", "classify", "ingestion.normalize"))
    for folder in ("src", "tests", "scripts"):
        for path in (ROOT / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for name in banned:
                for prefix in ("import ", "from "):
                    assert f"{prefix}{name}" not in text, f"{path.relative_to(ROOT)} imports {name}"
