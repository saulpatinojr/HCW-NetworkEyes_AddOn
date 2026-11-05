"""security.yml's pip-audit job audits what the image installs, minus the engine wheel itself.

The engine is a GitHub Release asset of the App (core-update.yml pins it by URL and sha256), not a PyPI package, so
pip-audit cannot look it up, and with `--strict` an unknown package fails the job ("Dependency not found on PyPI and
could not be audited", pull request 74). The export therefore leaves out both known distribution names and nothing
else: uv export keeps every transitive package, so the engine's own dependencies are still audited, and `--strict`
stays. Before the first adoption neither name is locked and the flags change nothing. These are static checks of the
workflow text; the export itself is exercised by CI on every pull request."""

import re
import shlex

from network_assessment import engine

from ..conftest import ROOT

TEXT = (ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "infrastructure" / "docker" / "Dockerfile").read_text(encoding="utf-8")
# A `uv export ...` command at the start of a line: a workflow `run:` line or a Dockerfile `RUN` line. The `RUN` and
# env-assignment prefix, a trailing backslash continuation and a following `&& ...` are dropped. Comments do not match.
EXPORT = re.compile(r"(?m)^\s*(?:RUN\s+)?(?:[A-Z_][A-Z0-9_]*=\S+\s+)*(uv export [^\n]*?)(?:\s*&&.*|\s*\\)?$")


def _export_lines(text: str) -> list[list[str]]:
    return [shlex.split(found) for found in EXPORT.findall(text)]


def _flag_values(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, a in enumerate(argv) if a == flag]


def test_pip_audit_exports_without_the_engine_and_stays_strict():
    job = TEXT.split("\n  pip-audit:\n", 1)[1].split("\n  base-follows-website:\n", 1)[0]
    exports = _export_lines(job)
    assert len(exports) == 1, "expected one uv export in the pip-audit job"
    argv = exports[0]
    assert "--frozen" in argv and "--no-dev" in argv and "--no-emit-project" in argv
    distributions = {distribution for _, distribution in engine.WHEEL_PACKAGES}
    assert set(_flag_values(argv, "--no-emit-package")) == distributions, "leave out exactly the engine's two names"
    audit = [line.strip() for line in job.splitlines() if "pip-audit -r" in line]
    assert audit == ['uv run pip-audit -r "${RUNNER_TEMP}/requirements.lock.txt" --strict'], audit


def test_the_image_build_keeps_the_engine_in_its_export():
    # The image needs the engine; only the audit leaves it out.
    exports = _export_lines(DOCKERFILE)
    assert exports, "the Dockerfile exports uv.lock for the image"
    for argv in exports:
        assert "--frozen" in argv and not _flag_values(argv, "--no-emit-package"), argv
