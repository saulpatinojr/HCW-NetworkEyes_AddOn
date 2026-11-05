"""The shipped stage of the Dockerfile applies Debian's security updates, and every CI build busts that layer's cache.

The base image is pinned by digest (versions.env), but a Debian security upload reaches the mirrors days before the
official image is rebuilt with it. On 2026-11-05 the website's Docker Scout gate refused the published image for
apt 3.0.3 (CVE-2026-109518, fixed in 3.0.4 from trixie-security) while the newest python:3.15-slim-trixie digest still
shipped 3.0.3, so no base bump could clear it (saulpatinojr/HCW-HybridCloudWorks#1562). The `lab` stage therefore runs
`apt-get upgrade` in a RUN of its own, and these checks pin the parts that make it safe and effective:

- the update and the upgrade run with `Acquire::Retries=0`: the apt doing the upgrade is still the base's, and the
  advisory needs a download retry to slip an unverified package in, so a mirror hiccup fails the build instead;
- the update runs with `--error-on=any`, so a missing index (trixie-security above all) fails the build instead of
  succeeding with a warning and upgrading nothing;
- the RUN names `${PUBLISH_CACHE_BUST}`, declared by `ARG` earlier in the stage, and both workflows that build the image
  pass a per-run value for it, so a rebuild of the same commit never reuses an older upgrade layer;
- the upgrade RUN is not chained to an unscoped `|| true` (that is how the earlier Dockerfile swallowed a failed
  upgrade), and the apt lists leave the layer.

These are static checks of the Dockerfile and workflow text. That the built image really carries the upgraded apt is
proven by building it (the `image` job of ci.yml) and by the website's weekly Scout check of the published image.
"""

import re
from pathlib import Path

# Computed from this file's place, not imported from conftest, so the file is the same in every add-on repository.
ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "infrastructure" / "docker" / "Dockerfile"
WORKFLOWS = ROOT / ".github" / "workflows"
# The stage publish-images.yml pushes and scans. A renamed or added shipped stage must be listed here with the upgrade.
SHIPPED_STAGES = {"lab"}
UPGRADE = re.compile(r"(?:^|\s)apt-get(?: -o \S+)* upgrade(?:\s|$)")
CACHE_BUST_VALUE = "${{ github.run_id }}-${{ github.run_attempt }}"


def instructions(path: Path) -> list[tuple[int, str, str]]:
    """(line number, KEYWORD, arguments) for each Dockerfile instruction, continuations joined, comments dropped."""
    result: list[tuple[int, str, str]] = []
    pending, start = "", 0
    for number, raw in enumerate(path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n"), start=1):
        line = raw.strip()
        if not pending and (not line or line.startswith("#")):
            continue
        if not pending:
            start = number
        if pending and line.startswith("#"):
            continue  # a comment line inside a continued instruction
        if line.endswith("\\"):
            pending += line[:-1].strip() + " "
            continue
        full = (pending + line).strip()
        pending = ""
        keyword, _, arguments = full.partition(" ")
        result.append((start, keyword.upper(), arguments.strip()))
    return result


def _stages() -> tuple[dict[str, list[tuple[int, str]]], dict[str, int]]:
    """RUN instructions by stage, and the line of each stage's `ARG PUBLISH_CACHE_BUST`."""
    runs: dict[str, list[tuple[int, str]]] = {}
    declared: dict[str, int] = {}
    current = ""
    for number, keyword, arguments in instructions(DOCKERFILE):
        if keyword == "FROM":
            parts = arguments.split()
            current = parts[2] if len(parts) >= 3 and parts[1].upper() == "AS" else ""
            runs.setdefault(current, [])
        elif keyword == "RUN" and current:
            runs[current].append((number, arguments))
        elif keyword == "ARG" and current and arguments.split("=")[0].strip() == "PUBLISH_CACHE_BUST":
            declared[current] = number
    return runs, declared


def test_every_shipped_stage_applies_the_distribution_security_updates() -> None:
    runs, declared = _stages()
    missing = SHIPPED_STAGES - set(runs)
    assert not missing, f"shipped stage(s) not found as a named FROM: {sorted(missing)}"
    for stage in sorted(SHIPPED_STAGES):
        upgrades = [(n, a) for n, a in runs[stage] if UPGRADE.search(a)]
        assert upgrades, f"stage {stage} has no apt-get upgrade in any RUN"
        for number, arguments in upgrades:
            assert stage in declared and declared[stage] < number, (
                f"line {number}: the upgrade RUN has no `ARG PUBLISH_CACHE_BUST` earlier in stage {stage}"
            )
            assert "${PUBLISH_CACHE_BUST}" in arguments, (
                f"line {number}: the upgrade RUN does not name PUBLISH_CACHE_BUST, so its cache key never changes"
            )
            assert arguments.index(" update") < arguments.index(" upgrade"), (
                f"line {number}: apt-get upgrade runs without apt-get update before it in the same RUN"
            )
            assert "apt-get -o Acquire::Retries=0 update --error-on=any" in arguments, (
                f"line {number}: the apt-get update before the upgrade runs with retries on, or can succeed with a"
                " warning when an index (trixie-security) cannot be fetched (missing --error-on=any)"
            )
            assert "apt-get -o Acquire::Retries=0 upgrade -y --no-install-recommends" in arguments, (
                f"line {number}: apt-get upgrade runs with retries on, or installs recommended packages"
            )
            # Any install in the same RUN keeps retries off too: if the upgrade had nothing to do, the apt doing the
            # install is still the base's.
            for match in re.finditer(r"apt-get(?: -o \S+)* install", arguments):
                assert "-o Acquire::Retries=0" in match.group(0), (
                    f"line {number}: an apt-get install in the upgrade RUN runs with retries on"
                )
            assert "|| true" not in arguments, (
                f"line {number}: `|| true` in the upgrade RUN would let a failed upgrade pass as a successful build"
            )
            assert "rm -rf /var/lib/apt/lists/*" in arguments, f"line {number}: the apt lists are left in the layer"


def test_no_other_stage_runs_apt() -> None:
    """The build stage never calls apt (its packages come hash-pinned from uv.lock), so there is no second apt path
    whose retries would need closing. A new apt call belongs in a shipped stage with the upgrade before it."""
    runs, _ = _stages()
    for stage, items in runs.items():
        if stage in SHIPPED_STAGES:
            continue
        for number, arguments in items:
            assert "apt-get" not in arguments, f"line {number}: stage {stage} calls apt-get; keep apt in the lab stage"


def _code(path: Path) -> str:
    """The workflow without its comment lines, so a comment can never satisfy an assertion."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("#"))


def test_publish_builds_pass_a_per_run_cache_bust() -> None:
    """Both build-push-action steps of publish-images.yml (the scan build and the push) pass the run id and attempt,
    so the pushed image is built with the same cache key as the scanned one and never with a stale upgrade layer."""
    code = _code(WORKFLOWS / "publish-images.yml")
    steps = [s for s in re.split(r"(?m)^ {6}- ", code) if re.search(r"(?m)^\s*uses:\s*docker/build-push-action@", s)]
    assert len(steps) == 2, f"expected the scan build and the push, found {len(steps)} build-push-action steps"
    for step in steps:
        block = re.search(r"(?ms)^\s*build-args:\s*\|\n((?:\s{12}.*\n?)+)", step)
        assert block, "build-args is not a block (`build-args: |`) listing one argument per line"
        args = [line.strip() for line in block.group(1).split("\n") if line.strip()]
        assert "EDITION=lab" in args, args
        assert f"PUBLISH_CACHE_BUST={CACHE_BUST_VALUE}" in args, (
            f"PUBLISH_CACHE_BUST is not the run id and attempt: {args}"
        )


def test_ci_image_build_passes_a_per_run_cache_bust() -> None:
    """ci.yml's image job builds the same stage with plain `docker build`; it passes the same per-run value."""
    code = _code(WORKFLOWS / "ci.yml")
    builds = re.findall(r"(?ms)^\s*docker build .*?-t addon:ci \.", code)
    assert len(builds) == 1, f"expected one `docker build` of addon:ci in ci.yml, found {len(builds)}"
    command = re.sub(r"\\\n\s*", " ", builds[0])
    assert "--build-arg EDITION=lab" in command, command
    assert '--build-arg "PUBLISH_CACHE_BUST=${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"' in command, command
