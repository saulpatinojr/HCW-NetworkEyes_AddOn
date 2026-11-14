"""The engine's static metadata: the `[[tool.uv.dependency-metadata]]` entry for the pinned engine distribution.

uv 0.13 and later re-resolve a lock by first sending a HEAD to the pinned wheel's address, and GitHub's signed download
link answered that HEAD with 401 (seen from a cloud session on 2026-11-13), so `uv lock` and `uv lock --check` failed.
With the entry uv does not ask the address. The entry is a copy of the wheel's own METADATA, so these tests hold it to
the pinned version, to the lock and to the wheel that is really installed, and they run core-update.yml's own lines:
the ENGINE_METADATA move in both jobs and the pull-request job's lock check, which lets the entry's version, and
nothing else in the lock's manifest, change. Ported from the Cloud Crawler add-on's
tests/security/test_engine_adoption.py and tests/unit/test_bump_core_pin.py, which guard the same entry there."""

import re
import subprocess
import sys
import tomllib
from importlib import metadata

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

from ..conftest import ROOT

UPSTREAM_RELEASES = "https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/download/"
PIN = re.compile(
    r'^\s*"(?P<dist>[a-z0-9-]+) @ (?P<url>' + re.escape(UPSTREAM_RELEASES) + r"engine-v(?P<tag>[0-9][0-9A-Za-z.+-]*)/"
    r'(?P<wheel>[a-z0-9_]+)-(?P<ver>[0-9][0-9A-Za-z.+-]*)-py3-none-any\.whl)",\s*#\s*ENGINE_REF\s+(?P<ref>\S+)\s*$',
    re.MULTILINE,
)
METADATA_MARKER = re.compile(r'^version = "(?P<ver>[^"]+)"[ \t]*#[ \t]*ENGINE_METADATA[ \t]*$', re.MULTILINE)
WORKFLOW = (ROOT / ".github" / "workflows" / "core-update.yml").read_text(encoding="utf-8")
BUMP_STEP = "name: Pin the wheel on the ENGINE_REF line, re-lock and regenerate the rule catalog"
NEW = "99.0.0"


def _pin():
    match = PIN.search((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert match, "pyproject.toml must carry the one-line ENGINE_REF pin that core-update.yml rewrites"
    return match


ENGINE = _pin()["dist"]


def _static_metadata(document):
    """The `[[tool.uv.dependency-metadata]]` entries of a parsed pyproject.toml, by package name."""
    entries = document.get("tool", {}).get("uv", {}).get("dependency-metadata", [])
    return {canonicalize_name(entry["name"]): entry for entry in entries}


def _lock():
    return tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))


def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _requirements(lines):
    """Requirement lines in a form that does not depend on how a tool ordered or spaced them. The extras and a URL are
    part of what is compared: the image installs the lock with `pip --no-deps`, so `pydantic[email]` and `pydantic` are
    different locks, and a requirement that names a URL is a different file."""
    found = []
    for line in lines:
        requirement = Requirement(line)
        found.append(
            (
                canonicalize_name(requirement.name),
                tuple(sorted(canonicalize_name(extra) for extra in requirement.extras)),
                str(requirement.specifier),
                requirement.url,
                str(requirement.marker),
            )
        )
    return sorted(found, key=repr)


def _extras(values):
    """Extras names as a set, in their normalised spelling."""
    return {canonicalize_name(value) for value in values or []}


# Every 3.X.Y from 3.0.0 to 3.40.99 (see the Cloud Crawler add-on's test for why each version is tried).
PYTHON_VERSIONS = [Version(f"3.{minor}.{patch}") for minor in range(41) for patch in range(100)]


def _python_versions_missing(engine_range, project_range):
    """The Python versions the project range allows and the engine's Requires-Python does not."""
    engine, project = SpecifierSet(engine_range or ""), SpecifierSet(project_range)
    assert PYTHON_VERSIONS[-1] not in project, "the project's requires-python reaches past the versions this test tries"
    return [str(version) for version in PYTHON_VERSIONS if version in project and version not in engine]


# --- the entry, the lock and the installed wheel -------------------------------------------------------------------


def test_engine_has_static_metadata_for_the_pinned_wheel():
    """Without it uv asks the wheel's address for the wheel's metadata every time it re-resolves the lock, and that
    request failed with 401. It must name the pinned distribution and be the pinned version's."""
    pin = _pin()
    assert pin["tag"] == pin["ref"] == pin["ver"] and pin["wheel"] == pin["dist"].replace("-", "_")
    entry = _static_metadata(_pyproject()).get(canonicalize_name(ENGINE))
    assert entry, f"pyproject.toml needs a [[tool.uv.dependency-metadata]] entry for {ENGINE}"
    assert entry["name"] == ENGINE and entry.get("version") == pin["ver"]
    assert entry.get("requires-dist"), "the entry must list the engine's dependencies (copy them from the wheel)"


def test_static_metadata_carries_the_marker_core_update_moves():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    found = METADATA_MARKER.findall(text)
    assert found == [_pin()["ver"]], "exactly one `version = ...  # ENGINE_METADATA` line, equal to the pinned version"
    assert text.splitlines().count(f'name = "{ENGINE}"') == 1, "core-update.yml finds the entry by this exact line"


def test_lock_manifest_records_the_same_static_metadata():
    """`uv lock --check` (ci.yml) already refuses a lock that disagrees with pyproject.toml; this names the reason."""
    wanted = _static_metadata(_pyproject()).get(canonicalize_name(ENGINE))
    recorded = {canonicalize_name(e["name"]): e for e in _lock().get("manifest", {}).get("dependency-metadata", [])}
    entry = recorded.get(canonicalize_name(ENGINE))
    assert wanted and entry, "uv.lock must record the engine's static metadata (run `uv lock`)"
    assert entry["version"] == wanted["version"]
    assert _requirements(entry["requires-dist"]) == _requirements(wanted["requires-dist"])
    assert _extras(entry.get("provides-extras", entry.get("provides-extra"))) == _extras(wanted.get("provides-extra"))


def test_static_metadata_does_not_set_requires_python():
    """Dependabot copies the first `requires-python` in uv.lock over every other one (dependabot-core,
    lock_file_updater.rb), so a different range in this entry would make the lock of every Dependabot pull request fail
    `uv lock --check`. The project's own range already limits where the engine can be installed."""
    assert "requires-python" not in _static_metadata(_pyproject())[canonicalize_name(ENGINE)]


def test_every_direct_url_package_in_the_lock_has_static_metadata():
    """A package pinned by URL with no static metadata makes uv ask that URL on every re-resolve. Any future URL pin
    must come with its metadata."""
    given = _static_metadata(_pyproject())
    urls = [
        (canonicalize_name(p["name"]), p["version"])
        for p in _lock()["package"]
        if isinstance(p.get("source"), dict) and "url" in p["source"]
    ]
    assert (canonicalize_name(ENGINE), _pin()["ver"]) in urls, "the engine is expected to be a direct URL package"
    for name, version in urls:
        assert name in given and given[name].get("version") == version, f"{name} {version} has no static metadata"


def test_static_metadata_matches_the_installed_wheel():
    """The metadata is a copy. This compares it with the wheel that is really installed, its `azure` extra included,
    so an upstream release that changes the engine's dependencies fails the bump pull request's compatibility check
    instead of shipping a lock that does not list them."""
    entry = _static_metadata(_pyproject())[canonicalize_name(ENGINE)]
    wheel = metadata.metadata(ENGINE)
    differing = _entry_differences(entry, wheel["Version"], metadata.requires(ENGINE), wheel.get_all("Provides-Extra"))
    assert not differing, f"the entry differs from the installed wheel in: {', '.join(differing)}"


def _entry_differences(entry, wheel_version, wheel_requires, wheel_extras):
    """Which of the entry's fields differ from what a wheel says."""
    found = []
    if wheel_version != entry["version"]:
        found.append("version")
    if _requirements(wheel_requires or []) != _requirements(entry["requires-dist"]):
        found.append("requires-dist")
    if _extras(wheel_extras) != _extras(entry.get("provides-extra")):
        found.append("provides-extra")
    return found


ADAPTED_ENTRY = {
    "version": "0.2.0",
    "requires-dist": ["pydantic>=2.13,<3", "azure-identity>=1.26.0 ; extra == 'azure'"],
    "provides-extra": ["azure"],
}
ADAPTED_REQUIRES = ["pydantic<3,>=2.13", 'azure-identity>=1.26.0; extra == "azure"']


def test_entry_comparison_passes_the_same_metadata_in_another_spelling():
    assert _entry_differences(ADAPTED_ENTRY, "0.2.0", ADAPTED_REQUIRES, ["azure"]) == []


@pytest.mark.parametrize(
    ("entry_change", "wheel_version", "wheel_requires", "wheel_extras", "expected"),
    [
        ({}, "0.3.0", ADAPTED_REQUIRES, ["azure"], ["version"]),
        ({"provides-extra": []}, "0.2.0", ADAPTED_REQUIRES, ["azure"], ["provides-extra"]),
        ({"provides-extra": ["azure", "aws"]}, "0.2.0", ADAPTED_REQUIRES, ["azure"], ["provides-extra"]),
        ({}, "0.2.0", ADAPTED_REQUIRES[:1], ["azure"], ["requires-dist"]),
        ({}, "0.2.0", ADAPTED_REQUIRES + ["orjson>=3"], ["azure"], ["requires-dist"]),
        ({}, "0.2.0", [ADAPTED_REQUIRES[0], "azure-identity>=1.26.0"], ["azure"], ["requires-dist"]),
    ],
    ids=["version", "extra-missing", "extra-extra", "requirement-gone", "requirement-new", "marker-dropped"],
)
def test_entry_comparison_names_every_field_that_differs(
    entry_change, wheel_version, wheel_requires, wheel_extras, expected
):
    entry = {**ADAPTED_ENTRY, **entry_change}
    assert _entry_differences(entry, wheel_version, wheel_requires, wheel_extras) == expected


def test_wheel_accepts_every_python_the_project_allows():
    """The entry leaves requires-python out on purpose, so this is the only automatic check of the engine's
    Requires-Python. A release that narrows it below what the project allows fails the bump pull request's
    compatibility check; a person then decides whether to raise the project's requires-python or not adopt it."""
    project = _pyproject()["project"]["requires-python"]
    missing = _python_versions_missing(metadata.metadata(ENGINE).get("Requires-Python"), project)
    assert not missing, f"requires-python {project} allows Python {missing[0]}..{missing[-1]}, which the engine refuses"


@pytest.mark.parametrize(
    ("engine_range", "first_missing"),
    [(">=3.15.3", "3.15.2"), ("<3.15.9", "3.15.9"), ("!=3.15.3", "3.15.3"), (">=3.16", "3.15.2")],
)
def test_python_range_check_notices_a_narrower_engine(engine_range, first_missing):
    assert _python_versions_missing(engine_range, ">=3.15.2,<3.16")[0] == first_missing


@pytest.mark.parametrize("engine_range", [">=3.14", ">=3.15.1,<3.17", "", None])
def test_python_range_check_accepts_the_same_or_a_wider_engine(engine_range):
    assert _python_versions_missing(engine_range, ">=3.15.2,<3.16") == []


@pytest.mark.parametrize(
    "changed",
    ["pydantic [email]>=2.13,<3", "pydantic @ https://example.invalid/p.whl", "orjson>=3"],
)
def test_requirement_comparison_notices_extras_urls_and_new_names(changed):
    assert _requirements([changed]) != _requirements(["pydantic>=2.13,<3"])


# --- core-update.yml's ENGINE_METADATA move, run as written ---------------------------------------------------------


def _step(header: str) -> str:
    """The step of core-update.yml whose header holds `header`: from that line to the next step."""
    start = WORKFLOW.index(header)
    following = re.search(r"(?m)^      - ", WORKFLOW[start:])
    return WORKFLOW[start : start + following.start()] if following else WORKFLOW[start:]


def _move_lines(step: str) -> str:
    """The step's ENGINE_METADATA move: from `meta=` to the `grep` that checks it, dedented to the run block."""
    lines = step.splitlines()
    start = [i for i, line in enumerate(lines) if line.strip().startswith('meta="version = ')]
    end = [i for i, line in enumerate(lines) if line.strip() == 'grep -qxF -- "$meta" pyproject.toml']
    assert len(start) == 1 and len(end) == 1 and start[0] < end[0], "the step must move the ENGINE_METADATA line once"
    return "\n".join(line[10:] for line in lines[start[0] : end[0] + 1]) + "\n"


@pytest.mark.parametrize("header", [BUMP_STEP, "id: regen"])
def test_both_jobs_move_the_static_metadata_after_the_pin_and_before_the_lock(header):
    """The file's header comment also says ENGINE_METADATA, so this looks inside each step: a search of the whole file
    would pass even if the move were deleted or moved after `uv lock`."""
    step = _step(header)
    pin = step.index("grep -cE '#[[:space:]]*ENGINE_REF[[:space:]]' pyproject.toml")
    move = step.index('meta="version = ')
    lock = re.search(r"(?m)^\s+(?:.*/)?uv lock\b", step)
    assert lock, "the step must lock"
    assert pin < move < lock.start(), "the ENGINE_METADATA line must move after the pin and before `uv lock`"
    assert not re.search(r"(?m)^\s*sed\s", step), "lines are replaced whole, never with a sed script"


def test_the_two_jobs_move_the_line_the_same_way():
    """The pull-request job regenerates pyproject.toml itself and compares it byte for byte with the bump job's, so the
    two moves must agree; only the temporary file differs."""
    bump = _move_lines(_step(BUMP_STEP)).replace(
        "pyproject.toml > pyproject.toml.new\nmv pyproject.toml.new pyproject.toml\n", "<write>\n"
    )
    regen = _move_lines(_step("id: regen")).replace(
        'pyproject.toml > "${RUNNER_TEMP}/pyproject.toml"\ncp "${RUNNER_TEMP}/pyproject.toml" pyproject.toml\n',
        "<write>\n",
    )
    assert "<write>" in bump and bump == regen


def _run_move(step: str, root, latest: str, dist: str, temp):
    env = {"PATH": "/usr/bin:/bin", "LATEST": latest, "DIST": dist, "RUNNER_TEMP": str(temp)}
    script = "set -euo pipefail\n" + _move_lines(step)
    return subprocess.run(["bash", "-c", script], cwd=root, env=env, capture_output=True, text=True)


@pytest.mark.parametrize("header", [BUMP_STEP, "id: regen"])
def test_the_move_changes_exactly_the_version_line(header, tmp_path):
    before = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(before, encoding="utf-8")
    (tmp_path / "temp").mkdir()
    proc = _run_move(_step(header), tmp_path, NEW, ENGINE, tmp_path / "temp")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    changed = [(a, b) for a, b in zip(before.splitlines(), after.splitlines(), strict=True) if a != b]
    assert changed == [(f'version = "{_pin()["ver"]}"  # ENGINE_METADATA', f'version = "{NEW}"  # ENGINE_METADATA')]
    entry = _static_metadata(tomllib.loads(after))[canonicalize_name(ENGINE)]
    assert entry["version"] == NEW and entry["requires-dist"] == _static_metadata(_pyproject())[ENGINE]["requires-dist"]


@pytest.mark.parametrize(
    ("edit", "dist"),
    [
        (lambda t: t.replace("  # ENGINE_METADATA", "  # ENGINE-METADATA"), ENGINE),
        (lambda t: t + f'version = "{_pin()["ver"]}"  # ENGINE_METADATA\n', ENGINE),
        (lambda t: t, "cna-azure-network-engine"),
    ],
    ids=["no-marker", "marker-twice", "entry-for-another-distribution"],
)
@pytest.mark.parametrize("header", [BUMP_STEP, "id: regen"])
def test_the_move_stops_on_a_pyproject_it_does_not_recognise(header, edit, dist, tmp_path):
    text = edit((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")
    (tmp_path / "temp").mkdir()
    proc = _run_move(_step(header), tmp_path, NEW, dist, tmp_path / "temp")
    assert proc.returncode != 0
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == text


# --- the pull-request job's lock check, run as written ---------------------------------------------------------------


def _verifier() -> str:
    """The Python the verify step feeds to `python3 -I -`, dedented."""
    lines = _step("id: verify").splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip().endswith("<<'PY'"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "PY")
    return "\n".join(line[10:] for line in lines[start + 1 : end]) + "\n"


def _new_url(version: str) -> str:
    return f"{UPSTREAM_RELEASES}engine-v{version}/{ENGINE.replace('-', '_')}-{version}-py3-none-any.whl"


def _bumped_lock(version: str = NEW) -> str:
    """This repository's uv.lock as a real bump to `version` writes it: the URL, the engine's version and the version
    of its static metadata move (the sha256 keeps its shape; the check reads its form, not its value)."""
    text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    old = _pin()["ver"]
    text = text.replace(_new_url(old), _new_url(version))
    engine_version = rf'(?m)^(name = "{re.escape(ENGINE)}"\nversion = )"{re.escape(old)}"$'
    text, moved = re.subn(engine_version, rf'\1"{version}"', text)
    assert moved == 2, "expected the engine's package entry and its static-metadata entry in uv.lock"
    return text


def _verify(tmp_path, new_text: str, latest: str = NEW):
    (tmp_path / "new.lock").write_text(new_text, encoding="utf-8")
    args = [str(tmp_path / "new.lock"), str(ROOT / "uv.lock"), ENGINE, _new_url(latest), latest]
    return subprocess.run(
        [sys.executable, "-I", "-", *args], input=_verifier(), cwd=tmp_path, capture_output=True, text=True
    )


def test_the_lock_check_accepts_a_bump_that_moves_the_static_metadata_with_the_pin(tmp_path):
    proc = _verify(tmp_path, _bumped_lock())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"only {ENGINE} changed" in proc.stdout


def _replace_first(text: str, old: str, new: str) -> str:
    """The manifest is at the top of uv.lock, so the first occurrence is the manifest's."""
    assert old in text, old
    return text.replace(old, new, 1)


TAMPERING = {
    # The static metadata stayed at the old version while the pin moved (uv would ask the address again).
    "metadata-not-moved": lambda t: re.sub(
        r'(\[\[manifest\.dependency-metadata\]\]\nname = "[^"]+"\nversion = )"[^"]+"', rf'\1"{_pin()["ver"]}"', t
    ),
    # The static metadata moved to another version than the release.
    "metadata-other-version": lambda t: re.sub(
        r'(\[\[manifest\.dependency-metadata\]\]\nname = "[^"]+"\nversion = )"[^"]+"', r'\1"98.0.0"', t
    ),
    # Its dependency list changed (a new dependency smuggled in through the metadata).
    "metadata-requires-dist": lambda t: _replace_first(
        t, 'requires-dist = ["pydantic>=2.13,<3", ', 'requires-dist = ["pydantic>=2.13,<3", "evil>=1", '
    ),
    # Its extras changed.
    "metadata-extras": lambda t: _replace_first(t, 'provides-extras = ["azure"]', 'provides-extras = ["azure", "x"]'),
    # Another package gained static metadata.
    "metadata-for-another-package": lambda t: _replace_first(
        t, "\n[[package]]\n", '\n[[manifest.dependency-metadata]]\nname = "evil"\nversion = "1.0"\n\n[[package]]\n'
    ),
    # Something else appeared in the manifest.
    "manifest-other-key": lambda t: _replace_first(
        t, "[[manifest.dependency-metadata]]", '[manifest]\nmembers = ["evil"]\n\n[[manifest.dependency-metadata]]'
    ),
    # The engine's static metadata is gone.
    "metadata-removed": lambda t: re.sub(r"\[\[manifest\.dependency-metadata\]\]\n(?:.+\n)+\n", "", t, count=1),
    # The engine's own [[package]] entry kept the old version while its URL and static metadata moved: the lock would
    # name the new wheel under the old version number.
    "package-version-not-moved": lambda t: re.sub(
        rf'(\[\[package\]\]\nname = "{re.escape(ENGINE)}"\nversion = )"[^"]+"', rf'\1"{_pin()["ver"]}"', t
    ),
    # The engine's own [[package]] entry moved to another version than the release.
    "package-other-version": lambda t: re.sub(
        rf'(\[\[package\]\]\nname = "{re.escape(ENGINE)}"\nversion = )"[^"]+"', r'\1"98.0.0"', t
    ),
}


# The cases that only the check of the engine's own version catches: each must be refused by that check, by name, so
# that a later reorder of the checks cannot hide it behind another refusal.
REFUSED_BY = {
    "package-version-not-moved": lambda: f"uv.lock: the locked engine is version {_pin()['ver']!r}, expected {NEW!r}",
    "package-other-version": lambda: f"uv.lock: the locked engine is version '98.0.0', expected {NEW!r}",
}


@pytest.mark.parametrize("tamper", sorted(TAMPERING))
def test_the_lock_check_refuses_every_other_change_to_the_manifest(tmp_path, tamper):
    tampered = TAMPERING[tamper](_bumped_lock())
    assert tampered != _bumped_lock(), "the tampering must change the lock"
    proc = _verify(tmp_path, tampered)
    assert proc.returncode == 1 and "::error::the bump artifact is refused" in proc.stdout, proc.stdout + proc.stderr
    if tamper in REFUSED_BY:
        assert REFUSED_BY[tamper]() in proc.stdout, proc.stdout + proc.stderr
