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


def test_provenance_headers_match_the_table():
    """Every ported module starts with the provenance header and is listed in PROVENANCE.md."""
    prov = (ROOT / "PROVENANCE.md").read_text(encoding="utf-8")
    ported = [
        "src/network_assessment/model/enforcer.py",
        "src/network_assessment/model/findings.py",
        "src/network_assessment/model/topology.py",
        "src/network_assessment/classify/topology.py",
        "src/network_assessment/rules/taxonomy.py",
        "src/network_assessment/rules/frameworks.py",
        "src/network_assessment/rules/azure_net.py",
        "src/network_assessment/rules/azure_bcdr.py",
        "src/network_assessment/rules/azure_cost.py",
    ]
    for rel in ported:
        lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        header = " ".join(line[1:].strip() for line in lines[:4] if line.startswith("#"))
        assert lines[0].startswith("# Ported from saulpatinojr/Work-Cloud_Network_Core "), rel
        assert "at 5d3b914; changes:" in header, rel
        assert f"`{rel}`" in prov, rel
