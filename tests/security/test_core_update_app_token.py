"""core-update.yml keeps the HCW Main Admin App key away from upstream code, and opens its bump pull request with the
App token, never with GITHUB_TOKEN.

Two jobs. `bump` runs the new engine (through this edition's tests and scripts) with a read-only GITHUB_TOKEN and no
secret. `pull-request` runs no project code: it verifies the bump job's artifact, then mints the App token and opens
the pull request. Code that runs in a step can reach later steps of the same job, which is why the key must never be in
a job that ran upstream code. A pull request opened with GITHUB_TOKEN starts no workflow, so the required checks never
run on it and it can never merge. The App's client ID is the repository variable HCW_MAIN_ADMIN_CLIENT_ID and its
private key is the repository secret HCW_MAIN_ADMIN_PRIVATE_KEY; no job runs in an environment. These are static checks
of the workflow text; they do not prove the credential works. A run with probe=true does (see the header of the
workflow), and the verification step was exercised against good and tampered artifacts (VALIDATION.md)."""

import os
import re
import subprocess

import pytest

from ..conftest import ROOT
from .test_base_update_workflow import BASH

TEXT = (ROOT / ".github" / "workflows" / "core-update.yml").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "infrastructure" / "docker" / "Dockerfile").read_text(encoding="utf-8")
VERSIONS = (ROOT / "infrastructure" / "docker" / "versions.env").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
PYTHON_VERSION_FILE = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
_PARTS = re.split(r"(?m)^  ([a-z-]+):\n", TEXT.split("\njobs:\n", 1)[1])[1:]
JOBS = dict(zip(_PARTS[::2], _PARTS[1::2], strict=True))  # job id -> its text
BUMP = re.split(r"(?m)^ {6}- ", JOBS["bump"].split("\n    steps:\n", 1)[1])[1:]
PR = re.split(r"(?m)^ {6}- ", JOBS["pull-request"].split("\n    steps:\n", 1)[1])[1:]
APP_STEP_OUTPUT = r"\$\{\{\s*steps\.app-token\.outputs\.token\s*\}\}"
# What "project code" looks like in a step: anything that installs or runs this repository's or the engine's code.
PROJECT_CODE = re.compile(
    r"\buv\s|uv==|\bpip\s|pytest|\bnpm\b|\bnpx\b|playwright|\bmake\b|ruff|scripts/|python -m|setup-python"
)


def _field(step: str, key: str) -> str:
    """The value of a step's own key (`if`, `id`, `uses`, `name`), or an empty string."""
    found = re.search(rf"(?m)^(?: {{8}})?{re.escape(key)}:[ \t]*(.*)$", step)
    return found.group(1).strip() if found else ""


def _with(step: str, key: str) -> str:
    """The value of a key under the step's `with:` (indented ten spaces)."""
    found = re.search(rf"(?m)^ {{10}}{re.escape(key)}:[ \t]*(.*)$", step)
    return found.group(1).strip() if found else ""


def _uses(steps: list[str], action: str) -> list[str]:
    return [s for s in steps if _field(s, "uses").split("@")[0] == action]


def _only(steps: list[str], action: str) -> str:
    found = _uses(steps, action)
    assert len(found) == 1, f"expected exactly one step using {action}"
    return found[0]


def _by_id(steps: list[str], step_id: str) -> str:
    found = [s for s in steps if _field(s, "id") == step_id]
    assert len(found) == 1, f"expected exactly one step with id {step_id}"
    return found[0]


def test_two_jobs_the_pull_request_job_needs_the_bump_job():
    assert set(JOBS) == {"bump", "pull-request"}
    assert re.search(r"(?m)^    needs: bump$", JOBS["pull-request"])
    assert re.search(r"(?m)^      changed: \$\{\{ steps\.refs\.outputs\.changed \}\}$", JOBS["bump"])


def test_the_bump_job_holds_no_secret_and_no_app_credential():
    bump = JOBS["bump"]
    assert "HCW_MAIN_ADMIN" not in bump and "create-github-app-token" not in bump
    assert not _uses(BUMP, "peter-evans/create-pull-request")
    assert not re.search(r"\bgh pr\b", bump)
    assert set(re.findall(r"secrets\.([A-Za-z0-9_]+)", bump)) <= {"GITHUB_TOKEN"}


def test_no_step_that_runs_project_code_is_given_a_token():
    runs_code = [s for s in BUMP if PROJECT_CODE.search(s)]
    assert len(runs_code) >= 3, "expected the setup, pin and compatibility steps"
    for step in runs_code:
        assert "GH_TOKEN" not in step and "secrets." not in step, _field(step, "name")
    # The token-holding steps come before any project code runs, and run none themselves.
    with_token = [s for s in BUMP if "GH_TOKEN" in s]
    assert [_field(s, "id") for s in with_token] == ["refs", "asset"]
    first_code = min(BUMP.index(s) for s in runs_code)
    assert all(BUMP.index(s) < first_code for s in with_token)


# The pull-request job may run uv for one thing only: `lock --no-build`, with the binary taken from the image the
# Dockerfile pins by digest. Anything else that installs, builds or runs code is refused, as in PROJECT_CODE.
PR_FORBIDDEN = re.compile(
    r"\buv\s+(?:run|sync|pip|tool|build|export|add|venv)\b|\buvx\b|uv==|\bpip\s|pytest|\bnpm\b|\bnpx\b|playwright"
    r"|\bmake\b|ruff|scripts/|python -m|setup-python"
)


def _versions_env(key: str) -> str:
    found = re.search(rf"(?m)^{key}=(\S+)$", VERSIONS)
    assert found, f"{key} is missing from infrastructure/docker/versions.env"
    return found.group(1)


def _docker_run_lines(step: str) -> list[str]:
    """Every `docker run` command of a step, with its backslash continuations joined into one line."""
    joined = re.sub(r"\\\n\s*", " ", step.split("run: |\n", 1)[1])
    return [line.strip() for line in joined.splitlines() if line.strip().startswith("docker run ")]


def test_the_pull_request_job_runs_no_project_code():
    for step in PR:
        assert not PR_FORBIDDEN.search(step), _field(step, "name") or _field(step, "uses")
    # uv runs once, to lock, inside the base image (the next test); the binary is the one copied out of the uv image.
    uv_calls = [line.strip() for line in JOBS["pull-request"].splitlines() if re.search(r"/uv\s+lock\b", line)]
    assert uv_calls == ['"$base" /uv lock --no-build --upgrade-package "$DIST"'], uv_calls
    # Its one interpreter call on the runner is this file's own inline script, isolated from the checkout and the
    # environment. (`.python-version`, `python:<tag>` image references and `BASE_PYTHON_VERSION` are not calls.)
    # Comment lines are left out: the one above that call says why it uses the runner's own interpreter.
    code = "\n".join(line for line in JOBS["pull-request"].splitlines() if not line.lstrip().startswith("#"))
    calls = re.findall(r"(?<![\w.:/-])python3?\b(?![:.-])[^\n]*", code)
    assert calls and all(c.startswith("python3 -I - ") for c in calls), calls


def test_the_lock_is_regenerated_inside_the_digest_pinned_base_image_with_its_own_interpreter():
    """`uv lock` needs an interpreter that satisfies `.python-version` and `requires-python`, and the job forbids uv to
    download one (UV_PYTHON_DOWNLOADS=never). The job installs no interpreter either, so every scheduled run failed at
    this step with `No interpreter found for Python 3.15` (runs 41944123703 and 41961781195, 2026-11-05). The lock now
    runs inside the base image every FROM of the Dockerfile pins by digest: the CPython the add-on ships with, verified
    by Docker like the uv binary, so what the runner image happens to carry no longer matters."""
    regen = _by_id(PR, "regen")
    # The image is read from versions.env, checked for shape and checked against the Dockerfile before it is run.
    assert "sed -n 's/^BASE_IMAGE=//p' infrastructure/docker/versions.env" in regen
    assert "sed -n 's/^BASE_DIGEST=//p' infrastructure/docker/versions.env" in regen
    assert '[[ "$base" =~ ^python:[0-9][0-9A-Za-z.-]*@sha256:[0-9a-f]{64}$ ]]' in regen
    assert 'grep -qF -- "FROM ${base} " infrastructure/docker/Dockerfile' in regen
    assert 'docker pull --quiet "$base"' in regen
    # One container, in the regen step only, as the runner's user, with no capabilities, a read-only root filesystem,
    # the checkout and /tmp as the only writable paths, the uv binary mounted read-only, and uv told to lock and
    # nothing else. No interpreter comes from the runner: nothing installs one and uv may not download one.
    assert [s for s in PR if "docker run" in s] == [regen]
    commands = _docker_run_lines(regen)
    assert len(commands) == 1, commands
    command = commands[0]
    assert command.endswith(' "$base" /uv lock --no-build --upgrade-package "$DIST"'), command
    for flag in (
        "--rm",
        '--user "$(id -u):$(id -g)"',
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--read-only",
        "--tmpfs /tmp:rw,nosuid,nodev,noexec,size=1g",
        "-e HOME=/tmp",
        "-e UV_CACHE_DIR=/tmp/uv-cache",
        "-e UV_PYTHON_DOWNLOADS=never",
        '-v "${RUNNER_TEMP}/uv-bin:/uv:ro"',
        '-v "${GITHUB_WORKSPACE}:/work"',
        "-w /work",
    ):
        assert f" {flag} " in f"{command} ", flag
    for forbidden in ("--privileged", "docker.sock", "--network", "--pid", "--ipc", "--cap-add", "--entrypoint"):
        assert forbidden not in command, forbidden
    assert "UV_PYTHON_DOWNLOADS=never" in command
    assert re.search(r"\buv\s+python\b", regen) is None and "--python" not in regen
    # The base image's CPython is the one the project pins, so the lock resolves there: versions.env (which
    # base-update.yml moves with every FROM) must stay on the line `.python-version` names and inside requires-python.
    base_python = _versions_env("BASE_PYTHON_VERSION")
    assert base_python == PYTHON_VERSION_FILE or base_python.startswith(PYTHON_VERSION_FILE + "."), (
        f".python-version {PYTHON_VERSION_FILE} is not the line of BASE_PYTHON_VERSION {base_python}"
    )
    requires = re.search(r'(?m)^requires-python = ">=([0-9.]+),<([0-9.]+)"$', PYPROJECT)
    assert requires, "requires-python must be the range >=<lowest patch>,<<next minor>"
    version = tuple(int(part) for part in base_python.split("."))
    lowest = tuple(int(part) for part in requires.group(1).split("."))
    ceiling = tuple(int(part) for part in requires.group(2).split("."))
    assert lowest <= version < ceiling, f"BASE_PYTHON_VERSION {base_python} is outside {requires.group(0)}"
    assert f"FROM {_versions_env('BASE_IMAGE')}@{_versions_env('BASE_DIGEST')} " in DOCKERFILE


def test_the_browser_suite_runs_on_the_node_it_chose():
    """The runner's own Node.js is older than the program's floor (saulpatinojr/HCW-HybridCloudWorks#1707), so the
    bump job installs Node.js 26 before the compatibility step runs npm, with no cache (files kept from earlier runs),
    and under the same condition as that step. The pull-request job has no Node.js step."""
    setup = _only(BUMP, "actions/setup-node")
    compat = _by_id(BUMP, "compat")
    assert not _uses(PR, "actions/setup-node")
    assert re.search(r"(?m)^ {8}with: \{ node-version: 26, package-manager-cache: false \}\s*$", setup), setup
    assert _field(setup, "if") == _field(compat, "if")
    assert BUMP.index(setup) < BUMP.index(compat)


def test_the_bump_job_hands_over_exactly_one_artifact_and_the_other_job_downloads_it():
    up = _only(BUMP, "actions/upload-artifact")
    down = _only(PR, "actions/download-artifact")
    assert _with(up, "name") == _with(down, "name") == "${{ env.ARTIFACT }}"
    assert PR.index(down) < PR.index(_by_id(PR, "verify"))


def test_the_pull_request_job_regenerates_pyproject_and_the_lock_itself():
    regen = _by_id(PR, "regen")
    assert PR.index(_by_id(PR, "expect")) < PR.index(regen) < PR.index(_only(PR, "actions/download-artifact"))
    # The uv binary comes from the digest-pinned image of the Dockerfile; Docker verifies the content.
    assert (
        "grep -oE 'ghcr\\.io/astral-sh/uv:[0-9][0-9.]*@sha256:[0-9a-f]{64}' infrastructure/docker/Dockerfile" in regen
    )
    assert re.search(r"(?m)^COPY --from=ghcr\.io/astral-sh/uv:[0-9.]+@sha256:[0-9a-f]{64} ", DOCKERFILE)
    assert "GH_TOKEN" not in regen and "secrets." not in regen
    verify = _by_id(PR, "verify")
    for name in ("pyproject.toml", "uv.lock"):
        assert f'cmp -s {name} "$dir/{name}"' in verify, f"the artifact's {name} must equal the regenerated one"
    # Only the catalog is taken from the artifact, and only as plain Markdown.
    take = next(s for s in PR if "bump/docs/rules/catalog.md" in s and "cp " in s)
    assert "bump/pyproject.toml" not in take and "bump/uv.lock" not in take
    assert "<[A-Za-z!/?]" in verify


def test_the_artifact_is_verified_before_the_token_is_minted():
    verify = _by_id(PR, "verify")
    app = _only(PR, "actions/create-github-app-token")
    expect = _by_id(PR, "expect")
    assert PR.index(expect) < PR.index(verify) < PR.index(app)
    assert "steps.verify.outcome == 'success'" in _field(app, "if")
    for check in (
        "docs/rules/catalog.md,outcome,pyproject.toml,uv.lock",
        "cmp -s pyproject.toml",
        "cmp -s uv.lock",
        "printf 'success\\n' | cmp -s - \"$dir/outcome\"",
        "printf 'failure\\n' | cmp -s - \"$dir/outcome\"",
        "only the engine moves in a bump",
        "sha256:[0-9a-f]{64}",
        "python3 -I - ",
    ):
        assert check in verify, check
    # The expected line is worked out in this job from the default branch and the release, not taken from the bump job.
    assert "needs.bump.outputs" not in verify and "needs.bump.outputs" not in expect
    assert re.search(r"(?m)^\s+DIST: \$\{\{ steps\.expect\.outputs\.dist \}\}$", verify)
    assert re.search(r"(?m)^\s+URL: \$\{\{ steps\.expect\.outputs\.url \}\}$", verify)


def test_wheels_are_chosen_by_exact_file_name_from_two_known_distributions():
    for step in (_by_id(BUMP, "asset"), _by_id(PR, "expect")):
        assert "for dist in network-assessment-azure-engine cna-azure-network-engine" in step
        assert 'grep -qxF -- "$wheel"' in step
        assert re.search(r'"\$\{#found\[@\]\}" -ne 1', step), "zero or several matches must fail"
        assert "network-assessment-azure-engine|cna-azure-network-engine" in step


REFUSE_NAME = "name: Refuse a run that is not on main"


def test_both_checkouts_take_the_commit_the_run_was_started_for_without_persisted_credentials():
    for steps in (BUMP, PR):
        checkout = _only(steps, "actions/checkout")
        assert _with(checkout, "persist-credentials") == "false"
        # github.sha: the commit on main the run was started for (the refusal below makes sure it is main).
        assert _with(checkout, "ref") == "${{ github.sha }}"
        assert steps.index(checkout) > 0 and steps[0].startswith(REFUSE_NAME), "the refusal comes before the checkout"
    assert "default_branch" not in TEXT
    # A checkout of a commit is a detached HEAD, where create-pull-request needs the base named.
    assert _with(_only(PR, "peter-evans/create-pull-request"), "base") == "main"


def test_both_jobs_refuse_a_run_that_is_not_on_main_first_and_visibly():
    for name, steps in (("bump", BUMP), ("pull-request", PR)):
        first = steps[0]
        assert first.startswith(REFUSE_NAME), f"{name}: the first step must be the main-only refusal"
        assert not _field(first, "if"), f"{name}: the refusal must always run"
        assert re.search(r'(?m)^ {8}env: \{ RUN_REF: "\$\{\{ github\.ref \}\}" \}$', first), name
        block = first.split("run: |\n", 1)[1]
        assert 'if [ "$RUN_REF" != "refs/heads/main" ]; then' in block
        assert re.search(r'echo "::error::[^"]*\$\{RUN_REF\}[^"]*"', block), f"{name}: the error must name the ref"
        assert re.search(r"(?m)^\s*exit 1$", block)
        assert "${{" not in block, f"{name}: no expression inside the shell"
    # A job-level `if:` would skip the bump job in silence; the pull-request job is also gated by one.
    assert not re.search(r"(?m)^    if:", JOBS["bump"]), "the bump job must refuse, not be skipped silently"
    job_if = "if: github.ref == 'refs/heads/main' && (needs.bump.outputs.changed == 'true' || inputs.probe)"
    assert re.search(rf"(?m)^    {re.escape(job_if)}$", JOBS["pull-request"])


def test_pull_request_is_opened_with_the_app_token_never_github_token():
    app = _only(PR, "actions/create-github-app-token")
    pr = _only(PR, "peter-evans/create-pull-request")
    assert _field(app, "id") == "app-token"
    assert PR.index(app) < PR.index(pr)
    assert re.fullmatch(APP_STEP_OUTPUT, _with(pr, "token"))
    assert "GITHUB_TOKEN" not in pr
    paths = pr.split("add-paths: |\n", 1)[1].split("\n          body:", 1)[0].split()
    assert paths == ["pyproject.toml", "uv.lock", "docs/rules/catalog.md"]


def test_every_step_that_runs_gh_pr_uses_the_app_token_after_it_was_minted():
    app = _only(PR, "actions/create-github-app-token")
    gh_pr = [s for s in PR if re.search(r"\bgh pr\b", s)]
    assert gh_pr, "the auto-merge step is missing"
    for step in gh_pr:
        assert re.search(rf"GH_TOKEN:\s*{APP_STEP_OUTPUT}", step)
        assert PR.index(app) < PR.index(step)


def test_auto_merge_never_reads_the_untrusted_outcome():
    merge = [s for s in PR if re.search(r"\bgh pr merge\b", s)]
    assert len(merge) == 1
    condition = _field(merge[0], "if")
    # The outcome comes from the job that ran upstream code, so it must not decide the merge. What does: the repository
    # variable, this job's own verification, and GitHub's required checks on the pull request.
    for part in (
        "steps.verify.outcome == 'success'",
        "vars.CORE_AUTOMERGE == 'true'",
        "steps.pr.outputs.pull-request-number != ''",
        "!inputs.probe",
    ):
        assert part in condition, part
    assert not re.search(r"outputs\.outcome|bump/outcome", merge[0]), "the auto-merge step must not read the outcome"
    assert 'gh pr merge --squash --auto "$PR_NUMBER"' in merge[0], "auto-merge waits for the required checks"
    assert "--admin" not in merge[0]
    # The outcome reaches only the pull request's text (title, labels, body), the step that takes the opposite
    # label off again on a refresh, and a warning that holds no token.
    readers = [s for s in PR if "steps.verify.outputs.outcome" in s]
    pr = _only(PR, "peter-evans/create-pull-request")
    assert len(readers) == 3 and pr in readers
    label = next(s for s in readers if "gh api -X DELETE" in s)
    assert re.search(r'/issues/\$\{PR_NUMBER\}/labels/\$\{OPPOSITE\}"', label), "the label step removes one label only"
    assert not re.search(r"gh pr\b|merge", label), "the label step must not touch the merge"
    assert "!inputs.probe" in _field(label, "if")
    warning = next(s for s in readers if s not in (pr, label))
    assert not re.search(r"GH_TOKEN|secrets\.|app-token|\bgh\b", warning), "the warning step must hold no token"


def test_token_action_is_pinned_to_a_full_commit_sha():
    app = _only(PR, "actions/create-github-app-token")
    assert re.fullmatch(r"actions/create-github-app-token@[0-9a-f]{40}( # .*)?", _field(app, "uses"))


def test_app_credential_is_the_hcw_main_admin_variable_and_secret():
    app = _only(PR, "actions/create-github-app-token")
    assert _with(app, "client-id") == "${{ vars.HCW_MAIN_ADMIN_CLIENT_ID }}"
    assert _with(app, "private-key") == "${{ secrets.HCW_MAIN_ADMIN_PRIVATE_KEY }}"
    # Only the token step is given the key.
    with_key = [s for s in BUMP + PR if "secrets.HCW_MAIN_ADMIN_PRIVATE_KEY" in s]
    assert with_key == [app], "the private key must reach the token step and no other step"
    assert TEXT.count("secrets.HCW_MAIN_ADMIN_PRIVATE_KEY") == 1


def test_workflow_reads_no_other_secrets():
    names = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", TEXT))
    assert names == {"GITHUB_TOKEN", "HCW_MAIN_ADMIN_PRIVATE_KEY"}
    for leak in ("toJSON(secrets", "secrets[", "secrets: inherit"):
        assert leak not in TEXT, f"{leak} would hand more than the one key to a step"


def test_app_token_is_limited_to_this_repository():
    app = _only(PR, "actions/create-github-app-token")
    # With `owner` set and `repositories` empty the action mints a token for every repository of the installation.
    # With no `owner`, an empty `repositories` falls back to the current repository, so this shape fails closed.
    assert not re.search(r"(?m)^\s*owner:", app), "owner must not be set: an empty repositories would widen the token"
    assert _with(app, "repositories") == "${{ github.repository }}"


def test_app_token_permissions_are_exactly_contents_and_pull_requests_write():
    app = _only(PR, "actions/create-github-app-token")
    granted = dict(re.findall(r"(?m)^\s*permission-([a-z-]+):\s*([a-z]+)\b", app))
    assert granted == {"contents": "write", "pull-requests": "write"}


def test_old_app_credential_is_gone():
    for old in ("admin-ops", "APP_CLIENT_ID", "APP_PRIVATE_KEY"):
        assert old not in TEXT, f"{old} must not appear in core-update.yml"
    assert "portfolio" not in TEXT.lower(), "the Portfolio App must not appear in core-update.yml"


def test_no_job_runs_in_an_environment():
    # The credential is a repository variable and secret, so no environment is needed (or wanted) on a job.
    assert not re.search(r"(?m)^\s*environment:", TEXT)


def test_empty_top_level_permissions_and_read_only_github_token_in_both_jobs():
    assert re.search(r"(?m)^permissions: \{\}\s*$", TEXT), "top-level permissions must stay empty"
    for job in JOBS.values():
        assert re.search(r"(?m)^    permissions:\n      contents: read\n    [a-z]", job), "each job: contents read only"
    assert len(re.findall(r"(?m)^\s*permissions:", TEXT)) == 3
    # The App token's inputs are `permission-*`, a different key; any other `<name>: write` would widen GITHUB_TOKEN.
    write_grant = re.search(r"(?m)^[ \t]+(?!permission-)[a-z-]+:[ \t]*write[ \t]*$", TEXT)
    assert not write_grant, "a permissions: block grants write"


def test_every_action_is_pinned_to_a_full_commit_sha():
    uses = [u for u in re.findall(r"(?m)^[ \t]*(?:- )?uses:[ \t]*(\S+)", TEXT) if not u.startswith("./")]
    assert len(uses) >= 7
    for use in uses:
        assert re.search(r"@[0-9a-f]{40}$", use), f"{use} is not pinned to a commit SHA"


def test_a_probe_run_never_reaches_a_step_that_writes_or_runs_code():
    # A manual run with probe=true must stay read-only even when a newer release exists (changed == 'true').
    writers = _uses(PR, "peter-evans/create-pull-request") + [
        s for s in PR if re.search(r"\bgh pr\b|gh api -X DELETE", s)
    ]
    assert len(writers) == 3, "expected the pull request step, the label step and the auto-merge step"
    for step in writers:
        assert "!inputs.probe" in _field(step, "if"), "a step that writes must be skipped on a probe"
    for step in BUMP:
        if PROJECT_CODE.search(step) or _field(step, "id") == "asset":
            assert "!inputs.probe" in _field(step, "if"), _field(step, "name")


def test_probe_step_only_reads_and_checks_the_token_covers_this_repository_only():
    probe = [s for s in PR if _field(s, "if") == "inputs.probe"]
    assert len(probe) == 1, "expected exactly one probe step"
    run = probe[0]
    assert re.search(r'gh api "repos/\$\{REPO\}"', run)
    assert re.search(r"gh api installation/repositories", run)
    assert re.search(r'test "\$\{covered\}" = "\$\{REPO\}"', run), "the probe must fail if the token covers more"
    # `gh api` turns into a POST as soon as it is given a field, so fields and bodies are as forbidden as -X, with
    # the value attached (-XPOST, -fname=value) or separate.
    writes = r"\bgh pr\b|\bgit\b|--method|\s-[XfF]|--field|--raw-field|--input"
    assert not re.search(writes, run), "the probe must not write"


# The compatibility step is the one that decides the bump pull request's label and title. It is run here the way GitHub
# runs it (bash -e), with `uv`, `npm` and `npx` replaced by stubs that fail one check at a time, because a regular
# expression over its text cannot show that a failure stops it: `set -e` does not exit on a command that fails inside
# an `a && b && c` list (bash skips the exit for every member but the last), which is how the first real bump (pull
# request 74, engine-v0.1.0) reported "compatible" with a refused catalog and 41 failing tests.
COMPAT_CHECKS = (
    "uv run ruff check .",
    "uv run python scripts/rules-doc.py --check",
    "uv run pytest -q",
    "CI=1 npx playwright test -c tests/e2e/playwright.config.ts",
)


def _run_body(step: str) -> str:
    body = step.split("run: |\n", 1)[1]
    return "\n".join(line[10:] for line in body.splitlines()) + "\n"


def test_the_compatibility_step_runs_each_check_as_its_own_command():
    compat = _by_id(BUMP, "compat")
    assert _field(compat, "continue-on-error") == "true", "its outcome is the label, so the job goes on either way"
    lines = [line.strip() for line in _run_body(compat).splitlines() if line.strip()]
    assert lines[0] == "set -euo pipefail"
    for check in COMPAT_CHECKS:
        assert check in lines, f"{check!r} must be a line of its own"
    for line in lines[1:]:
        assert not re.search(r"&&|\|\||;", line), f"a joined list hides a failure from set -e: {line!r}"


@pytest.mark.skipif(BASH is None, reason="bash is not available on this computer")
@pytest.mark.parametrize("failing", [*COMPAT_CHECKS, None], ids=lambda c: c or "all-pass")
def test_the_compatibility_step_fails_when_any_check_fails(tmp_path, failing):
    """Every stubbed tool exits 0 except the one check named by `failing`, which exits 1; the step must then exit
    non-zero (GitHub records `steps.compat.outcome == 'failure'`). With every check passing it exits 0."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = (
        "#!/usr/bin/env bash\n"
        'line="$(basename "$0") $*"\n'
        'if [ -n "${FAILING:-}" ] && [ "$line" = "$FAILING" ]; then echo "stub: $line fails" >&2; exit 1; fi\n'
        'echo "stub: $line"\n'
    )
    for name in ("uv", "npm", "npx"):
        (bin_dir / name).write_text(stub, encoding="utf-8", newline="\n")
        (bin_dir / name).chmod(0o755)
    # A sentinel after the step's own lines: with the last check failing, "no later check ran" is vacuous, so the
    # sentinel is what proves that bash stopped.
    sentinel = "compatibility-sentinel"
    script = tmp_path / "compat.sh"
    script.write_text(_run_body(_by_id(BUMP, "compat")) + f'echo "{sentinel}"\n', encoding="utf-8", newline="\n")
    # The stubs see the command without its `CI=1` prefix (bash passes that as the environment).
    env = {**os.environ, "PATH": os.pathsep.join([bin_dir.as_posix(), os.environ.get("PATH", "")])}
    if failing is not None:
        env["FAILING"] = failing.removeprefix("CI=1 ")
    result = subprocess.run(
        [BASH, "-e", script.as_posix()], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60
    )
    if failing is None:
        assert result.returncode == 0, result.stdout + result.stderr
        assert all(c.removeprefix("CI=1 ") in result.stdout for c in COMPAT_CHECKS)
        assert sentinel in result.stdout
    else:
        assert result.returncode != 0, f"{failing!r} failed but the step passed:\n{result.stdout}{result.stderr}"
        later = [c for c in COMPAT_CHECKS if COMPAT_CHECKS.index(c) > COMPAT_CHECKS.index(failing)]
        assert not any(c.removeprefix("CI=1 ") in result.stdout for c in later), "a later check ran after a failure"
        assert sentinel not in result.stdout, "a command after the compatibility checks ran after a failure"
