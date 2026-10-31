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

import re

from ..conftest import ROOT

TEXT = (ROOT / ".github" / "workflows" / "core-update.yml").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "infrastructure" / "docker" / "Dockerfile").read_text(encoding="utf-8")
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


def test_the_pull_request_job_runs_no_project_code():
    for step in PR:
        assert not PR_FORBIDDEN.search(step), _field(step, "name") or _field(step, "uses")
    uv_calls = re.findall(r"(?m)^.*uv-bin\"?\s+\S.*$", JOBS["pull-request"])
    assert len(uv_calls) == 1 and ' lock --no-build --upgrade-package "$DIST"' in uv_calls[0], uv_calls
    # Its one interpreter call is this file's own inline script, isolated from the checkout and the environment.
    calls = re.findall(r"\bpython3?\b[^\n]*", JOBS["pull-request"])
    assert calls and all(c.startswith("python3 -I - ") for c in calls), calls


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


def test_both_checkouts_take_the_default_branch_without_persisted_credentials():
    for steps in (BUMP, PR):
        checkout = _only(steps, "actions/checkout")
        assert _with(checkout, "persist-credentials") == "false"
        assert _with(checkout, "ref") == "${{ github.event.repository.default_branch }}"


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


def test_auto_merge_never_rests_on_the_bump_jobs_report_alone():
    merge = next(s for s in PR if re.search(r"\bgh pr merge\b", s))
    condition = _field(merge, "if")
    for part in (
        "steps.verify.outcome == 'success'",
        "steps.verify.outputs.outcome == 'success'",
        "vars.CORE_AUTOMERGE == 'true'",
        "!inputs.probe",
    ):
        assert part in condition, part
    assert "--auto" in merge, "auto-merge waits for the required checks; never merge directly"


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
    writers = _uses(PR, "peter-evans/create-pull-request") + [s for s in PR if re.search(r"\bgh pr\b", s)]
    assert len(writers) == 2, "expected the pull request step and the auto-merge step"
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
