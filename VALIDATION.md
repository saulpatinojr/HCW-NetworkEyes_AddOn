# Validation

What was executed for this edition and what was not, per run. "Here" is the authoring container (no Docker daemon, PyPI
and the Playwright CDN reachable through a proxy). Dates are the run date.

## Run 2026-11-13, fifth part (uv 0.13.8; HCW-HybridCloudWorks#1707)

uv moves from 0.13.7 to 0.13.8 in `ci.yml` (`UV_VERSION`), `security.yml`, the `bump` job of `core-update.yml` and the Dockerfile's uv image, and the runbook's live lock instructions follow ([HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707)). The App (HCW-NetworkEyes_App) makes the same move in its workflows, whose Dockerfiles Dependabot had already moved to 0.13.8. Run from `main` at `38aac8e`. Toolchain: Linux cloud session, CPython 3.15.2, uv 0.13.8 installed with `pip --require-hashes` (wheel sha256 `e18a57b8…8984`) into a throwaway virtual environment outside the repository, and uv 0.13.7 for the comparisons.

| Check | Executed here | Result |
| --- | --- | --- |
| The uv image digest: an anonymous `HEAD` of `https://ghcr.io/v2/astral-sh/uv/manifests/0.13.8` asking for an image index | yes | `Docker-Content-Digest: sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85`, content type `application/vnd.oci.image.index.v1+json`; the same digest HCW-NetworkEyes_App's Dockerfiles pin for 0.13.8 |
| `ci.yml`'s uv check replayed (the `grep -Fq` lines, with the digest above in place of `docker buildx`) | yes | the Dockerfile line and the `"uv==0.13.8"` lines in `security.yml` and `core-update.yml` all match. As a control, the same check against `main`'s Dockerfile (still 0.13.7) fails with `the uv image is not ghcr.io/astral-sh/uv:0.13.8@…` |
| `uv sync` (0.13.8) | yes | `Resolved 52 packages`, `Checked 51 packages`, nothing to change |
| `uv lock --check -v` (0.13.8) with an empty cache | yes | exit 0, `Resolved 52 packages`; no request to `github.com` or `githubusercontent.com` (the static metadata entry of the second part still keeps uv away from the engine's address), so the `401` of the first part does not come back |
| `uv lock` (0.13.8) with an empty cache, on a scratch copy | yes | exit 0, `uv.lock` byte for byte the same as the committed one |
| The runbook's `uvx uv@0.13.8 lock`, run in bash on the same scratch copy (the runbook gives it for PowerShell; the command is the same) | yes | `Resolved 52 packages`, `uv.lock` unchanged |
| The image's `uv export` (the Dockerfile's flags) and `security.yml`'s export, under uv 0.13.7 and 0.13.8 | yes | byte-identical in both cases (sha256 `c56eb00a…e5b1` and `142323e5…094a`) |
| `ruff check .`, `ruff format --check .`, `python scripts/rules-doc.py --check` | yes | `All checks passed!`; 74 files already formatted; `docs/rules/catalog.md is in sync (422 lines)` |
| `pytest -q --cov=src` | yes | 1162 passed; coverage 97.07% |
| actionlint 1.7.12 (without shellcheck, not installed here) and zizmor 1.31.1 `--offline` with `.github/zizmor.yml`, over every workflow as `ci.yml` runs them | yes | actionlint no findings; zizmor `No findings to report` (2 ignored, 35 suppressed) |
| hadolint | **no** | not installed here; the Dockerfile changed only in the uv image's version and digest |
| Docker image build, and CI itself on uv 0.13.8 | **no** | no Docker daemon here; the pull request's CI is the real test |
| `make e2e` | **no** | this change touches neither the pane nor the API |

## Run 2026-11-13, fourth part (round two of the workflow runtime check; HCW-HybridCloudWorks#1707)

`tests/security/test_workflow_runtime_setup.py` is replaced by round two of the check, from the canonical Python copy in HCW-NetworkEyes_App (commit `8ac3118`, with the fourth review round's fixes, [HCW-NetworkEyes_App#395](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/395)), which is kept the same as the website's `scripts/workflow-runtime-setup.test.mjs` (merged as `9e2e0dd`, [HCW-HybridCloudWorks#1719](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1719); issue [HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707)). Only this repository's own lists differ, and the wording of the docstring and comment lines that ran past this repository's 120 columns (the one long pattern, `ASSIGNMENT`, is written as two adjacent strings, which Python joins into the same value). Run from `main` at `5e74d1b`. Toolchain: Linux cloud session, CPython 3.15.2, uv 0.13.7 from a throwaway virtual environment outside the repository.

| Check | Executed here | Result |
| --- | --- | --- |
| The port's code against HCW-NetworkEyes_App's copy at `8ac3118` | yes | the two files' syntax trees are identical once the docstrings and the four lists (`RUNNER_DEFAULT_ALLOWED`, `INDIRECT_RUNTIME`, `PIPX_ALLOWED`, `BELOW_FLOOR_ALLOWED`) are set aside; the earlier canonical copy, as a control, differs |
| `uv sync`, `ruff check .`, `ruff format --check .`, `python scripts/rules-doc.py --check` | yes | `Checked 51 packages`; `All checks passed!`; 74 files already formatted; the rules page matches |
| `pytest -q --cov=src` | yes | 1160 passed; coverage 97.07%. `tests/security/test_workflow_runtime_setup.py` alone: 699 passed (354 before) |
| The check over this repository's workflows | yes | the same findings as the copy on `main`: no step reported that its lists do not name, no `pipx` step, no set-up step below 3.15 or 26, and no composite action to read. Its one listed exception stays and is still needed: the `core-update.yml` step that checks `uv.lock` with the runner's own Python (standard library only, in a job that holds the App key) is still reported without it |
| The same answers as the canonical copy, and the JavaScript copies | yes | 66,627 cases (23,958 command readings, each with its two shell texts; 42,498 `pipx` cases; 171 condition cases), and the 104 files (100 workflows, 4 composite actions) of the nine HCW repositories cloned here plus two folders of made-up workflows for the new rules (jobs read, unset steps, `pipx` problems, floor problems): 0 disagreements with the canonical Python copy at `8ac3118` and between the five Python ports. The website's JavaScript copy (`9e2e0dd`) and the MigrateOrchestrator App's (`78feda5`) do not have the fourth round's fixes yet: they agree with the canonical copy as it was before them (`62ee0cc`) on every case, and differ from it now exactly on the 3,085 cases those fixes change (28 answers; the rest are how a GitHub expression is written in the shell text) and on the made-up workflow for them; the fixes reach them in their own pull requests |
| The new checks catch a real step | yes | in a scratch copy of the CloudCrawler add-on's `.github` (not this working tree), a job added to `ci.yml` with `PIPX_DEFAULT_PYTHON=/usr/bin/python3 pipx run zizmor .` and a literal `run: |` script running `node x.js`: 2 failed, naming both steps; the same `node` in a folded `run: >-` script is one line of text, as GitHub runs it, and is not reported |
| actionlint, zizmor, and CI on GitHub | **no** | no workflow changed, and nothing was pushed; the pull request's CI runs the test on GitHub |
| `make e2e` | **no** | this change touches neither the pane nor the API |

## Run 2026-11-13, third part (the finished workflow runtime check; HCW-HybridCloudWorks#1707)

`tests/security/test_workflow_runtime_setup.py` is replaced by the finished Python copy from HCW-NetworkEyes_App (commit `3810402`, [HCW-NetworkEyes_App#394](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/394)), which is kept the same as the website's `scripts/workflow-runtime-setup.test.mjs` ([HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707)). Only this repository's own lists differ, and the wording of three comment lines that ran past this repository's 120 columns. Toolchain: Linux cloud session, CPython 3.15.2, uv 0.13.7 installed with `pip` into a throwaway virtual environment outside the repository.

| Check | Executed here | Result |
| --- | --- | --- |
| The port's code against HCW-NetworkEyes_App's copy at `3810402` | yes | the two files' syntax trees are identical once the docstrings and the four lists (`RUNNER_DEFAULT_ALLOWED`, `INDIRECT_RUNTIME`, `PIPX_ALLOWED`, `BELOW_FLOOR_ALLOWED`) are set aside |
| `uv sync`, `ruff check .`, `ruff format --check .`, `python scripts/rules-doc.py --check` | yes | clean, 74 files; `docs/rules/catalog.md is in sync (422 lines)` |
| `pytest -q --cov=src` | yes | 815 passed; coverage 97.07%. `tests/security/test_workflow_runtime_setup.py` alone: 354 passed (121 before) |
| The check over this repository's workflows | yes | one step reported, the same one as before: `core-update.yml > pull-request > Verify the artifact matches ... > python`, already in `RUNNER_DEFAULT_ALLOWED` with its reason. Every other step that runs Python or Node.js (now counting `pytest`, `bash -c` scripts and the rest) comes after a set-up step that covers it, every set-up step asks for 3.15 or 26, and no workflow runs `pipx` |
| The scripts the workflows call, read one level deep | yes | every Python script a step calls (`scripts/follow_website_base.py`, `rules-doc.py`) is run with `python` or `python3`, which the check reads, and starts no other runtime; `scripts/package-repository.sh` (the `package` job, which sets nothing up) runs only `zip` and `unzip`. So `INDIRECT_RUNTIME` stays empty |
| The same answers as HCW-NetworkEyes_App's copy | yes | 21,840 shared cases (command reading with its shell text, the `pipx` check and the condition rules) and the 97 workflow files of the nine HCW repositories cloned here (unset steps, `pipx` problems, floor problems): no disagreement, and none between the three add-ons' copies |
| The new checks catch a real step | yes | a job with `bash -c 'pytest -q'` and `pipx run zizmor .` steps added to the end of `ci.yml` on the working tree: 2 failed, naming both steps; the file was then restored |
| actionlint, zizmor, and CI on GitHub | **no** | no workflow changed, and nothing was pushed; the pull request's CI runs the test on GitHub |
| `make e2e` | **no** | this change touches neither the pane nor the API |

## Run 2026-11-13, second part (the engine's static metadata; HCW-HybridCloudWorks#1707)

The first part of this run (below) found that uv 0.13.7 could not lock this repository from here: its first request for the engine wheel is a HEAD, which GitHub's signed download link answered with `401`. This part ports the Cloud Crawler add-on's fix ([HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707)): `pyproject.toml` gives uv the engine's metadata in a `[[tool.uv.dependency-metadata]]` entry, whose version line carries the marker `ENGINE_METADATA` and moves with the pin. `core-update.yml` replaces that line whole in both jobs (the same `awk` replacement as its `ENGINE_REF` line), and the pull-request job's lock check, which used to refuse any change outside the packages as "its header changed", now lets the engine's static-metadata version, and nothing else in the manifest, change. Toolchain as in the first part, with uv 0.13.7 for every uv command below.

| Check | Executed here | Result |
| --- | --- | --- |
| The entry's contents, from the pinned wheel itself | yes | `curl -L` (a GET) of `https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/download/engine-v0.1.5/network_assessment_azure_engine-0.1.5-py3-none-any.whl` gave a file with sha256 `689d15be41006ea48710f96cc7ca93e039dffde9c5a54d5f03b4db5f2824fdbc`, the value in `uv.lock`; its `network_assessment_azure_engine-0.1.5.dist-info/METADATA` says `Name: network-assessment-azure-engine`, `Version: 0.1.5`, `Requires-Python: >=3.14`, `Requires-Dist: pydantic<3,>=2.13`, `Provides-Extra: azure` and seven `Requires-Dist` lines for the `azure` extra (`azure-identity>=1.26.0`, `azure-mgmt-resourcegraph<9,>=8.0.0`, `azure-mgmt-network>=33.1.0`, `azure-mgmt-monitor<8,>=7.0.0`, `azure-monitor-query<3,>=2.0.0`, `azure-mgmt-costmanagement<6,>=5.0.0`, `azure-mgmt-loganalytics<15,>=14.0.0`, each `; extra == "azure"`). The entry lists the extra too (`provides-extra = ["azure"]`), because leaving it out changed the engine's entry in `uv.lock` when tried on a scratch copy; this edition never installs the extra, and the exported image requirements are the same. The entry copies those `Requires-Dist` lines in the wheel's own spelling, leaves `Requires-Python` out on purpose (Dependabot rewrites every `requires-python` in the lock) |
| `uv lock -v` with an empty cache (`--cache-dir` a new folder) | yes | exit 0, `Resolved 52 packages`; the log shows 100 requests, 50 to `pypi.org` and 50 to `files.pythonhosted.org`, **none to `github.com` or `githubusercontent.com`** (the only line naming the engine's address is uv's `Searching for a compatible version`, which sends nothing) |
| `uv lock --check -v`, another empty cache | yes | exit 0, `Resolved 52 packages`, no request at all |
| What `uv lock` changed in `uv.lock` | yes | the header `revision = 3` became `5` (uv 0.13.7's lock format) and the `[manifest]` block with the entry was added; no package entry changed, the engine's URL and sha256 included |
| `uv sync` and `uv sync --frozen` (0.13.7) | yes | `Checked 51 packages`, nothing to change |
| The image's `uv export` (the Dockerfile's flags) and `security.yml`'s export, 0.13.7, against the first part | yes | byte-identical to the exports measured in the first part, under both uv versions |
| `uv lock --check` with uv 0.11.32 (the version `main` still uses) | yes | exit 0: a lock written by 0.13.7 also passes under 0.11.32 |
| `ruff check .`, `ruff format --check .`, `python scripts/rules-doc.py --check` | yes | clean, 74 files; `docs/rules/catalog.md is in sync (422 lines)` |
| `pytest -q --cov=src` | yes | 582 passed; coverage 97.07%. Among them the new `tests/security/test_engine_static_metadata.py` (44 tests): the entry against the pin, the lock and the installed wheel; the ENGINE_METADATA move of both jobs run as written on a copy of `pyproject.toml` (only the version line changes; it stops on a missing or doubled marker, or on an entry for another distribution, and leaves the file as it was); the two jobs move the line the same way; and the pull-request job's lock check run as written, which accepts a bumped lock and refuses 7 other changes to the manifest. `tests/security/test_workflow_runtime_setup.py` and `test_core_update_app_token.py` pass |
| The new tests fail when the change is undone (each on the working tree, restored afterwards) | yes | `core-update.yml` from before this part: 13 failed. The lock check with its new manifest lines removed (so it ignores the manifest): 7 failed, every tampering case. `pyproject.toml` without the entry: 8 failed |
| actionlint 1.7.12 (without shellcheck, not installed here) and zizmor 1.31.1 `--offline` with `.github/zizmor.yml` | yes | actionlint no findings. zizmor first reported one `adhoc-packages` finding: the Playwright install in `core-update.yml` moved down when lines were added above it, and `.github/zizmor.yml` ignores it by line number, as its comment says. The line is the same pinned `npm install "@playwright/test@1.63.0"`; its number in `.github/zizmor.yml` was moved to match, and zizmor then reported `No findings to report` |
| The PowerShell commands added to the runbook | **no** | no PowerShell here. The METADATA reader is the Cloud Crawler add-on's, run there in Windows PowerShell 5.1; the download line was adapted for this repository and was not run. The `gh api` call inside it was run here with `--jq` and returned the expected tag |
| A real engine bump through `core-update.yml`, a Dependabot run, and CI on GitHub | **no** | no new engine release exists, nothing was pushed, and Dependabot runs only from `main`. Whether GitHub Actions also gets the `401` was not tested; with the entry it no longer matters for `uv lock --check` |

## Run 2026-11-13 (uv 0.13.7 and ruff 0.17.4; HCW-HybridCloudWorks#1707)

uv (the tool that installs the Python packages and keeps `uv.lock`) moves from 0.11.32 to 0.13.7 in `ci.yml`, `security.yml`, the `bump` job of `core-update.yml` and the Dockerfile's uv image (which the `pull-request` job copies its uv from) ([HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707)). Toolchain: Linux cloud session, CPython 3.15.2, uv 0.13.7 installed with `pip` into a throwaway virtual environment outside the repository, and the session's own uv 0.11.32. ruff moves from 0.17.3 to 0.17.4 and its `target-version` to `py315`, as in the Cloud Crawler add-on.

| Check | Executed here | Result |
| --- | --- | --- |
| The uv image digest: an anonymous `HEAD` of `https://ghcr.io/v2/astral-sh/uv/manifests/0.13.7` asking for an image index | yes | `Docker-Content-Digest: sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490`, content type `application/vnd.oci.image.index.v1+json` (the multi-platform index, which is what `docker buildx imagetools inspect` prints in `ci.yml`); the same digest `HCW-NetworkEyes_App` pins for 0.13.7. The old pin `df4cae8f…504c` is still what the registry gives for 0.11.32 |
| `ci.yml`'s uv check replayed (the `grep -Fq` lines, with the digest above in place of `docker buildx`) | yes | the Dockerfile line and the `"uv==0.13.7"` lines in `security.yml` and `core-update.yml` all match |
| `uv lock --check` with uv 0.13.7 on this repository | **no, blocked** | uv 0.13.7 first sends a `HEAD` (a request for the file's headers only) to the engine wheel's address `https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/download/engine-v0.1.5/network_assessment_azure_engine-0.1.5-py3-none-any.whl`; GitHub redirects it to a signed link on `objects.githubusercontent.com`, which answered `401`, so the command stopped with an error. A plain `GET` of the same address redirects to `release-assets.githubusercontent.com` and downloads. uv 0.11.32 sends no `HEAD`, which is why it never showed. This is the failure the Cloud Crawler add-on met in Dependabot's runs and fixed with a `[[tool.uv.dependency-metadata]]` entry (the engine's dependency list written in `pyproject.toml`, so uv need not ask the address). Whether GitHub Actions gets the same `401` was not tested: if it does, the `uv lock --check` step in `ci.yml` and the `uv lock` in `core-update.yml` fail until this repository gets the same entry |
| The same lock resolved by uv 0.13.7 with the engine's metadata supplied from a config file outside the repository (a scratch copy) | yes | 52 packages, every one identical to the committed lock; the only differences are the header `revision = 5` (uv 0.13.7's format; 0.13.7's `--check` accepts the committed `revision = 3`, tried on a scratch copy) and the `[manifest]` block the scratch config adds. So uv 0.13.7 itself changes nothing in `uv.lock` |
| `uv sync --frozen --all-packages` and `uv export --frozen` with uv 0.13.7 | yes | both work: installing from the lock downloads the wheel with a `GET` and never sends the `HEAD` |
| The image's `uv export` (the Dockerfile's flags) and `security.yml`'s export, under uv 0.11.32 and 0.13.7 | yes | byte-identical in both cases |
| ruff 0.17.3 → 0.17.4 in `pyproject.toml`, `target-version = "py315"` in `ruff.toml`; `uv lock --upgrade-package ruff` with uv 0.11.32 (the uv that can resolve this lock here; see above) | yes | `Updated ruff v0.17.3 -> v0.17.4`, only ruff's entry moved, and it is identical to the Cloud Crawler add-on's; `uv lock --check` (0.11.32) passes |
| `uv sync`, `ruff check .`, `ruff format --check .` | yes | ruff 0.17.4; `All checks passed!`; 73 files already formatted, so the new target found nothing to change |
| `python scripts/rules-doc.py --check` | yes | `docs/rules/catalog.md is in sync (422 lines)` |
| `pytest -q --cov=src` | yes | 538 passed; coverage 97.07%. `tests/security/test_workflow_runtime_setup.py`, `test_core_update_app_token.py` and `tests/unit/test_follow_website_base.py` together: 271 passed |
| actionlint 1.7.12, hadolint 2.14.0 and zizmor 1.31.1 `--offline`, the versions `ci.yml` pins (binaries checked against its sha256 values) | yes, actionlint without shellcheck | no findings from any of them. shellcheck is not installed here, so actionlint ran with `-shellcheck=`; the shell lines changed only in a version number and a hash |
| Docker image build, and CI itself on uv 0.13.7 | **no** | no Docker daemon here, and nothing was pushed. The first pull request run is the real test of the `uv lock --check` step (see the row about the `401` above) |
| `make e2e` | **no** | no Playwright browser is installed here, and this change touches neither the pane nor the API |

## Run 2026-11-12 (workflow jobs choose their Python and Node.js; HCW-HybridCloudWorks#1707)

Four jobs ran Python or Node.js on the runner's own versions (Python 3.14 and Node.js 24 on the `ubuntu-26.04` image),
below the program's floors of 3.15 and 26
([HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707)): `base-update.yml`
`plan` and `open-pr`, and `core-update.yml` `bump` (npm) and `pull-request` (the verify step's `python3 -I -`). The
first three now install their version with the pinned `actions/setup-python` (from `.python-version`) or
`actions/setup-node` (26), with no cache. The `pull-request` job keeps the runner's own `python3` on purpose: its check
uses only the standard library (`tomllib`), and the job holds the App key, so it installs nothing; a comment above the
call says so, and the new check lists it as its one exception. Toolchain: Linux cloud session, uv-managed CPython 3.15.2.

| Check | Executed here | Result |
| --- | --- | --- |
| `tests/security/test_workflow_runtime_setup.py`, the new check over every workflow | yes | 30 passed. Its workflow reader was compared with PyYAML (CPython 3.13, outside the test) on all 367 steps of the four add-ons' workflows: the same jobs, containers and step `name`, `uses` and `run` values |
| The new check fails when a fix is undone | yes, on a scratch worktree | with the `plan` job's setup-python step removed from `base-update.yml`, 1 failed and 29 passed, naming the two `plan` steps that run `follow_website_base.py` (`Compare this repository's base image with the website's pin (writes nothing)` and `Decide whether the pull request job has anything to do …`); with the step put back, 30 passed |
| `ruff check .`, `ruff format --check .`, `uv lock --check`, `python scripts/rules-doc.py --check` | yes | clean (73 files); lock current; `docs/rules/catalog.md` in sync (422 lines) |
| `pytest -q --cov=src` | yes | 447 passed (2 new tests on the edited workflows, 30 in the new check); coverage 97.07% |
| actionlint 1.7.12 (with shellcheck 0.11.0) and zizmor 1.31.1 `--offline` with `.github/zizmor.yml`, the versions `ci.yml` pins | yes | actionlint no findings; zizmor `No findings to report` (2 ignored: the two `npm install @playwright/test` lines) |
| A real `base-update` run, and a real `core-update` bump, on the chosen versions | **no**, after the merge | `base-update` runs daily at 07:37 UTC; `core-update` only does this work when the App publishes a new engine release |

## Run 2026-11-09 (release 0.1.3 prepared)

This run prepares the version bump only and publishes nothing. The release exists so that the public lab runs engine
0.1.5 (adopted on `main` by [pull request 97](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/97)). Toolchain:
the scratch environment of the runs below (CPython **3.15.0b4**, filled from `uv export --frozen` plus the `engine-v0.1.5`
wheel, sha256 `689d15be…fdbc`, equal to `uv.lock`); tests run with `PYTHONPATH=src`.

| Check | Executed here | Result |
| --- | --- | --- |
| The version in every place that says it: `pyproject.toml`, `uv.lock` (the `hcw-addon-network-assessment` entry), `__version__`, `repository.manifest.json`, the sample output in `docs/operations/runbook.md` | yes | all say `0.1.3`. `uv lock` could not run here (no 3.15.1 interpreter), so the lock's one project-version line was changed to match what 0.1.2's re-lock changed; `ci.yml`'s `uv lock --check` verifies it. The runbook's sample health output also had stale rule and model versions (`2026.10.0`, `lab-1.0.0`) and now shows `2026.11.1` and `1.5.0` |
| `ruff check .`, `ruff format --check .`, `python scripts/rules-doc.py --check` | yes | clean (72 files); `docs/rules/catalog.md` in sync (422 lines) |
| `pytest -q --cov=src` | yes | 415 passed; coverage 97.07%. Includes `test_manifest_version_matches_pyproject` (the three version strings agree) |
| Publish dry run on the merged commit (`publish-images.yml` by hand; its header says a manual run builds, checks the boundary and scans, and never pushes) | **no**, after the merge | run once this merges, on the merge commit the `v0.1.3` tag will point at |
| Trivy scan, push, provenance, SBOM, attestation, digest | **no**, CI on a `v*` tag only | the `v0.1.3` tag is the owner's call |

## Run 2026-11-08 (the image states MIT AND Apache-2.0 and carries both licence texts)

Toolchain: the same scratch environment as the run below (CPython **3.15.0b4**, filled from `uv export --frozen` plus
the `engine-v0.1.2` wheel; `uv sync` refuses 3.15.0b4 because the project requires `>=3.15.1`); tests run with
`PYTHONPATH=src`. ruff 0.17.3, pytest 9.1.1. Lint tools from PyPI in a separate scratch environment: actionlint 1.7.12
(the version `ci.yml` pins), hadolint 2.15.1 and zizmor 1.32.0 (`ci.yml` pins 2.14.0 and 1.31.1).

| Check | Executed here | Result |
|---|---|---|
| `ruff check .` and `ruff format --check .` | yes | clean (72 files) |
| `python scripts/rules-doc.py --check` | yes | `docs/rules/catalog.md` in sync (422 lines) |
| `pytest -q --cov=src --cov-fail-under=85` | yes | 408 passed; coverage 97.06%. Without the new `tests/security/test_image_licences.py` (6 tests) the suite is 402, the count `main` had before this change |
| `actionlint` (all workflows) | yes | exit 0, no findings |
| `hadolint infrastructure/docker/Dockerfile` | yes | exit 0, no findings |
| `zizmor --offline .github/workflows` | yes | no findings (2 ignored, 39 suppressed, as configured) |
| Docker image build, the `image` job's label and licence-file checks, the publish dry run, Playwright e2e | **no**, CI only | no Docker daemon here; the pull request's `image` job builds the image and runs the new checks |

## Run 2026-11-08 (the interim port is deleted; ADR-0006)

Toolchain: CPython **3.15.0b4** (the only 3.15 `uv python install 3.15` offered here; the project requires
`>=3.15.1`, so `uv sync` refused it), in a scratch virtual environment outside the repository filled from
`uv export --frozen --no-emit-project --all-groups` plus the `engine-v0.1.2` wheel downloaded through the GitHub API
(its sha256 `084ea06e…708a1` equals the one in `uv.lock`); tests run with `PYTHONPATH=src`. ruff 0.17.3, pytest 9.1.1,
pydantic 2.14.1.

| Check | Executed here | Result |
|---|---|---|
| `uv sync` | tried, **refused** | `.python-version` resolves to 3.15.0b4, which `requires-python >=3.15.1` excludes; the scratch environment above stood in |
| The same suite on `main` before the change (baseline) | yes | 515 passed, coverage 96.03% |
| `ruff check .` and `ruff format --check .` | yes | clean (71 files) |
| `python scripts/rules-doc.py --check` | yes | `docs/rules/catalog.md` in sync (422 lines), unchanged by this change |
| `pytest -q --cov=src` | yes | 400 passed, 0 skipped; coverage 97.06% (gate 85). The 115 fewer tests are the deleted port tests and the one normaliser comparison; three were added (startup refusal in a fresh interpreter, the `EngineNotInstalled` message, an empty rule text) and one replaced (the port stays deleted) |
| `python -m compileall -q src tests scripts` | yes | exit 0 |
| `IDENTITY_ENDPOINT=http://169.254.169.254 python -c "import network_assessment.app"` | yes | `EditionBoundaryError: refusing to start: identity environment present (IDENTITY_ENDPOINT)` |
| Docker image build, the `image` job, Playwright e2e, CodeQL, pip-audit | **no**, CI only | no Docker daemon or Playwright here; the pull request's own checks cover them |

## Run 2026-11-05 (release 0.1.2 prepared)

This run prepares the version bump only and publishes nothing. The release exists so that the published image carries
`apt 3.0.4` (website issue [saulpatinojr/HCW-HybridCloudWorks#1562](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1562);
the Dockerfile change is [pull request 79](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/79), already on
`main`). This pull request changes nothing in the lab application but `__version__`; what moved in `src/` since 0.1.1 (the engine
adoption path and the additive `engine` block in `/api/health` and `/api/rules`) is already on `main` and listed in
`CHANGELOG.md` under 0.1.2. "Here" is the owner's Windows
workstation: CPython 3.15 managed by uv against the committed `uv.lock` (`--frozen` everywhere); the re-lock ran with
`uvx uv@0.11.32`, the uv CI uses, not the workstation's uv 0.12.0.

| Check | Executed here | Result |
| --- | --- | --- |
| The version in every place that says it: `pyproject.toml`, `uv.lock` (the `hcw-addon-network-assessment` entry), `__version__`, `repository.manifest.json` and the sample output in `docs/operations/runbook.md`; `uvx uv@0.11.32 lock` then `uvx uv@0.11.32 lock --check` | yes | all `0.1.2`; the lock differs from `main` in that one version line only (`revision = 3` untouched); `lock --check` exits 0 |
| `docs/api/openapi.yaml` `info.version` | not changed | stays `0.1.0`: this pull request adds no route, field or error code (the additive `engine` block since 0.1.1 was documented there without moving the document version), and no test ties it to `__version__` |
| `uv run ruff check . && uv run ruff format --check .` and `uv run python scripts/rules-doc.py --check` | yes | clean (94 files); `docs/rules/catalog.md` in sync (422 lines) |
| `uv run pytest -q tests/security tests/unit` | yes | 507 passed in 13 s. It includes `test_manifest_version_matches_pyproject` (`pyproject.toml`, `repository.manifest.json` and `__version__` agree) and `test_health_is_flat_and_complete` (the body's `version` and the `X-Addon-Version` header equal `__version__`); the bash-backed workflow tests passed here too |
| `uv run pytest -q --cov=src --cov-fail-under=85` (the full suite with coverage), `tests/contract` | no | the pull request's `test` job runs them; only the version string changed in `src/` |
| Local image build and the runbook's `curl` against a live server | no | the Dockerfile is unchanged since [pull request 79](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/79), whose own run recorded `apt 3.0.4` inside a local build; the merged commit's publish dry run (next row) builds it again on CI |
| Publish dry run on the merged commit (`gh workflow run publish-images.yml --ref main`; the header says a manual run builds, checks the boundary and scans, and never pushes) | **no**, after the merge | it is run once this change is on `main`, and its Trivy result is recorded on the website issue before the owner tags `v0.1.2` |
| Trivy scan, push, provenance, SBOM, attestation, digest | **no**, CI on a `v*` tag only | `publish-images.yml`; only a `v*` tag pushes, and `v0.1.2` is the owner's call |
| Playwright e2e, CodeQL, gitleaks, dependency-review, `ci.yml` on the pull request | **no**, CI only | not run here; the pull request's own checks cover them |

## Run 2026-11-05 (the first real bump pull request; the compatibility step and the pip-audit export)

The scheduled `core-update.yml` run opened [pull request 74](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/74) (`engine-v0.1.0`) as `compatible`; its `test`,
`rules-doc` and `pip-audit` checks failed. This run fixes the two workflow defects that showed (the engine's own
differences stay, see `docs/whats-new-upstream.md`). "Here" is the owner's Windows workstation: CPython 3.15 managed by
uv, uv 0.12.0 locally against the committed `uv.lock` (`--frozen` everywhere), Git Bash for the stubbed step.

| Check | Executed here | Result |
| --- | --- | --- |
| `uv sync --frozen`, `uv run ruff check . && uv run ruff format --check .`, `uv run python scripts/rules-doc.py --check` | yes | clean (93 files); `docs/rules/catalog.md` in sync |
| `uv run pytest -q --cov=src --cov-report=term-missing --cov-fail-under=85` | yes | 505 passed, 6 skipped (the engine wheel is not installed on this branch); coverage 97 percent |
| The new tests against the old workflow text (both files swapped for `main`'s copies, then restored byte for byte) | yes | 4 failed, 29 passed: the shape test, the stubbed step with `ruff` failing and with `rules-doc --check` failing (a failing `pytest`, last in the old list, was never hidden), and the pip-audit export test |
| The stubbed compatibility step on the fixed text, one check failing at a time and all passing | yes | exits non-zero on each of the four failures and 0 when all pass (`test_the_compatibility_step_fails_when_any_check_fails`) |
| `uv export --frozen … --no-emit-package network-assessment-azure-engine --no-emit-package cna-azure-network-engine` on the bump branch's lock and on `main`'s lock | yes | both exit 0; the same fourteen packages at the same versions; the engine is absent from the bump's export and its `pydantic` dependency present |
| `uv run pip-audit -r <that export> --strict` on the bump branch's export | yes | `No known vulnerabilities found` |
| `actionlint` 1.7.12 on `core-update.yml` and `security.yml` (shellcheck off) | yes | no findings apart from `ubuntu-26.04` being unknown to this actionlint version (already so on `main`) |
| `pip-audit` with a real pull request in the `security` workflow | no | the pull request's own `pip-audit` job runs it; the bump branch gets the fix on the next scheduled run |
| `make e2e` | no | nothing here touches the pane or the API |


This run moves the base image to the website's `python:3.15.2-slim-trixie` pin and every place that names the Python
minor line with it (CHANGELOG, Unreleased, Changed). "Here" is the owner's Windows workstation: CPython 3.15.2 installed
by uv into its managed directory (`uv python install 3.15.2`), uv 0.11.32 run through `uvx uv@0.11.32` (the version CI
uses), Docker Desktop with engine 29.9.2 and Buildx 0.38.1 on the local `desktop-linux` context.

| Check | Executed here | Result |
| --- | --- | --- |
| Every compiled package in `uv.lock` has a CPython 3.15 wheel on PyPI (pydantic-core 2.50.1, charset-normalizer 3.5.2, coverage 7.17.0, msgpack 1.2.4, tomli 2.5.0) | yes, PyPI's JSON API | 30, 32, 34, 23 and 18 `cp315` wheels; nothing is built from source |
| `uv lock` (0.11.32) after `requires-python` moved, then `uv lock --check` | yes | 51 packages resolved; no package version changed, only wheel lists and markers; `--check` exit 0 |
| `uv sync --frozen` on CPython 3.15.2 | yes | exit 0; `.venv` runs `Python 3.15.2` |
| `uv run ruff check . && uv run ruff format --check .` and `uv run python scripts/rules-doc.py --check` | yes | clean (92 files); `docs/rules/catalog.md` in sync (422 lines) |
| `uv run pytest -q --cov=src --cov-report=term-missing --cov-fail-under=85` | yes | 496 passed, 6 skipped (the engine wheel is not installed); coverage 97 percent |
| Startup refusal under an identity endpoint (`IDENTITY_ENDPOINT=http://169.254.169.254`) | yes | exit 1, as the `test` job expects |
| `docker build -f infrastructure/docker/Dockerfile --build-arg EDITION=lab` on the new base | yes | exit 0; the build stage prints `edition boundary: no cloud SDK in /install`; image 203 MB |
| The `image` job's steps of `ci.yml`, by hand against that image | yes | `import azure` fails; `import fastapi, pydantic, uvicorn` succeeds; `engine: none interim port … (ENGINE_REF none)`; `Python 3.15.2` equals `BASE_PYTHON_VERSION=3.15.2`; licence label `MIT`; runs as uid 10001; `ensurepip` and the pip binaries are gone from the `python3.15` paths |
| A disposable container (`--rm`, port on 127.0.0.1 only) answers `GET /api/health` and `POST /api/assessments` with the sample export | yes | `{"ok":true,…,"edition":"lab",…}` and HTTP 201 |
| The `lint` job's `FROM` check and the `base-follows-website` comparison of `security.yml`, by hand against the website's `lab-image/versions.env` read from `main` on 2026-11-03 | yes | both `FROM` lines equal `BASE_IMAGE@BASE_DIGEST`; the pin equals the website's `python:3.15.2-slim-trixie@sha256:8c13a3f3…` |
| `python scripts/follow_website_base.py --website-env <the website's file> --check` | yes | `changed=false`, exit 0 (the daily run has nothing to move once this merges) |
| `npx playwright test -c tests/e2e/playwright.config.ts` | no | not run here; the `e2e` job runs it on the pull request |
| `pip-audit` on the exported runtime set | no | not run here; the `pip-audit` job runs it on the pull request |
| `base-follows-website` green on `main` | no | that job runs on `main` and weekly, not on pull requests; read its first run after the merge |

## Run 2026-10-31 (`core-update.yml` runs from `main` only; auto-merge ignores the bump job's report)

The first step of both jobs refuses a run whose `github.ref` is not `refs/heads/main`, the `pull-request` job's `if:`
also requires it, both checkouts take `github.sha` (they took the default branch's tip before), and
`create-pull-request` gets `base: main`. The auto-merge step's condition is now the verify step's success,
`CORE_AUTOMERGE == 'true'`, a pull request number and not a probe; it no longer reads the untrusted outcome.

| Check | Executed here | Result |
| --- | --- | --- |
| `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python scripts/rules-doc.py --check` | yes | clean (92 files); catalog in sync |
| `uv run pytest -q --cov=src` | yes | 496 passed, 6 skipped |
| `tests/security/test_core_update_app_token.py` | yes | 24 passed, with three new or rewritten tests: the refusal is the first step of each job, has no `if:`, reads the ref through `env` and names it in an `::error::`; the `bump` job has no job-level `if:` and the `pull-request` job's requires `main`; both checkouts use `github.sha` and the pull request step names `base: main`; the auto-merge condition holds the variable, the verify step and `!inputs.probe` and nothing that reads the outcome, and only the pull request step and a token-free warning read it |
| Mutation check: six breakages, one at a time | yes | each made at least one test fail: either job's refusal step removed, the `main` condition removed from the job's `if:`, the refusal's `exit 1` replaced with `true`, `ref: github.sha` removed from a checkout, `steps.verify.outputs.outcome == 'success'` added back to the auto-merge condition; the workflow was restored byte for byte |
| `actionlint` 1.7.12 on `core-update.yml` (shellcheck off, not installed) | yes | no findings apart from `ubuntu-26.04` being unknown to this actionlint version (already so on `main`) |
| Required checks on `main`, read-only (`gh api repos/saulpatinojr/HCW-NetworkEyes_AddOn/rules/branches/main`) | yes | the active "Protect main" ruleset (id 25825146) requires `lint`, `test`, `image`, `package`, `e2e`, `rules-doc`, `pip-audit`, `secret-scan`, `dependency-review`, which covers the bump job's compatibility check (lint, catalog drift, tests, e2e) |
| `make e2e` | no | nothing here touches the pane or the API |
| The workflow on GitHub, including a refused run from a branch | no | not run; the value of `CORE_AUTOMERGE` could not be read from this session |

Known limitation: a manual run takes the workflow file itself from the branch it was started on, so a branch that also
edits `core-update.yml` can delete these guards. Closing that needs the App key moved to an environment whose
deployment branches are `main` only (a settings change, not made here).

## Run 2026-10-31 (adopting the engine wheel `engine-v0.1.0`)

"Here" for this run is a Linux cloud session: Python 3.14.6, uv 0.11.32, Node 22.23.4, Playwright 1.63.0 with the
session's own chromium, Docker engine 29.9.2. Its outbound traffic goes through a proxy. The App's releases API and
the Actions API were not reachable; `git` reads of the App and the release asset download were. Nothing here can
start a GitHub workflow, so `core-update.yml` was **not** run on GitHub: its bump step was run by hand in a scratch
copy (below), and the real run is the next scheduled one after this change merges.

| Check | Executed here | Result |
| --- | --- | --- |
| `uv sync`, `uv run ruff check . && uv run ruff format --check .` | yes | clean (92 files) |
| `uv run python scripts/rules-doc.py --check` | yes | in sync (422 lines); the port's catalog is unchanged by this change |
| `uv run pytest -q --cov=src` (port, as this change leaves the repository) | yes | 466 passed, 3 skipped (the wheel-only normalizer comparison), coverage 97.13% (gate 85) |
| `make e2e` equivalent (`playwright test -c tests/e2e/playwright.config.ts`, CI=1, from a scratch copy so the worktree stays clean) | yes | 4 passed on the port |
| The released wheel itself: `git clone --depth 1 --branch engine-v0.1.0` of the App, installed from `packages/cna-azure-network-engine`; and the release asset downloaded | yes | the clone is commit `e5863c8`; the downloaded wheel's sha256 is `a609b80059fca7b22057b464a0c41895b324e21dc3e28d569a6e0894e94bd1ba`, equal to the value recorded on 2026-10-24 |
| Port and wheel side by side over the three samples (rule registry, findings, unknowns, classifier, normalizer) | yes | registry digest, `RULES_VERSION`, live-only set, classifier and normalizer agree; the five differences are listed in `docs/whats-new-upstream.md` (entry of 2026-10-31) |
| The bump `core-update.yml` makes, rehearsed in a scratch copy: its own `bump` step script (extracted from the workflow), with a stand-in for the one `gh api` call that returns the release's wheel name `cna_azure_network_engine-0.1.0-py3-none-any.whl` | yes | the marker line became `"cna-azure-network-engine @ https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/download/engine-v0.1.0/cna_azure_network_engine-0.1.0-py3-none-any.whl",  # ENGINE_REF 0.1.0`; `uv lock` downloaded the asset and recorded the same sha256; `rules-doc.py --write` refused the wheel's texts (AZ-COST-002 remediation, "expected") and the step went on, as designed. Before `allow-direct-references` was added, `uv lock` failed in the build backend, so no bump could have built |
| The compatibility check on that bump (`uv sync --frozen`, `ruff check`, `rules-doc.py --check`, `pytest -q`) | yes | ruff clean; `rules-doc.py --check` fails (the hedge word); `pytest`: 41 failed, 428 passed. Every failure is one of the five engine differences: 35 rule-text cases, 3 evidence-reference cases, the report hedge check, and the two pinned sample expectations (AZ-NET-007 fires twice and AZ-NET-025 not at all). The lab's own adaptations pass on the wheel: normalizer parity on all three samples, the registry digest, live-only rules in `unknowns[]`, the API and the edition boundary. So the real bump will be labelled `needs-adaptation` and will not merge: auto-merge, if turned on, keeps waiting because the same failures fail its required checks |
| The browser suite on that bump | yes | 4 passed on the wheel |
| The `image` job's steps of `ci.yml`, on a port build and on a wheel build | yes, with a sandbox-only Dockerfile copy | The committed Dockerfile cannot download packages inside a build here (the proxy's certificate is not in the build container; the unchanged port build fails the same way). A scratch copy that adds only the proxy's CA bundle to the build stage (verification stays on) built both: `pip install --require-hashes` installed the wheel from the lock; no cloud SDK in `/install`; `engine: interim port …` and `engine: cna-azure-network-engine 0.1.0`; `image python: Python 3.14.8 (BASE_PYTHON_VERSION=3.14.8)`; licence label MIT |
| The new Python-version check against a wrong and a missing `BASE_PYTHON_VERSION` | yes | exit 1 with `the built image runs 'Python 3.14.8', but BASE_PYTHON_VERSION is 3.14.9`, and exit 1 with `BASE_PYTHON_VERSION is missing`; exit 0 with the real file |
| The rewritten manifest check of `test_edition_boundary.py` against a lock with a cloud SDK | yes | fails for a locked `azure-identity` package and for an `azure-identity` requirement without an extra marker; passes on the bump's lock, whose only Azure names are the engine's `[azure]` extra metadata |
| Review round on PR #66: the two-job `core-update.yml`, dry run from the workflow's own step scripts (`bump`: asset, pin and stage; `pull-request`: expect and verify), with a stand-in for the two read-only `gh api` calls | yes | Asset selection: the `cna_` wheel among a tarball or a foreign wheel is chosen; no known wheel, two known wheels, or only a signature file fails. Verify: the genuine artifact passes with outcome `failure` and with `success` (the outcome sets only the label); refused with a message for each of: outcome not one word, an extra file, a symlink, a new dependency in `pyproject.toml`, another URL, another changed line, another package's hash changed in `uv.lock`, a new locked package, the engine wheel without a sha256, the engine pulling in a new dependency, a control character in the catalog, the catalog heading gone. The dry run also found that the workflow's uv 0.11.32 writes `revision = 3` where `main`'s lock says `5`; the verifier allows that one header field to differ (an integer), nothing else |
| Second review round: the pull-request job regenerates `pyproject.toml` and `uv.lock` itself (`uv lock --no-build`) and requires the artifact's copies to be byte-identical; dry run as above, with the local uv 0.11.32 standing in for the binary the job copies out of the digest-pinned uv image (no image was pulled and no external binary run here) | yes | `uv lock --no-build` ran no build backend and gave a lock byte-identical to the bump job's; the genuine artifact passes; every earlier tampered case is still refused, and three more are: another sha256 for the engine wheel in a structurally valid lock (which the structural check alone would have accepted), an extra `pyproject.toml` line (another package index), and a `<script>` tag in the catalog |
| The new pin check (`test_the_engine_that_runs_is_the_one_pyproject_pins`) | yes | passes on the port (`none`) and on the wheel (`0.1.0`); fails for "port installed, pin says 0.1.0", "wheel installed, pin says none" and "wheel 0.1.0 installed, pin says 0.2.0" |
| Third review round: the pull-request job's regeneration runs inside the digest-pinned base image (`docker run --rm --user … --read-only … python:3.15.2-slim-trixie@sha256:8c13a3f3… /uv lock --no-build --upgrade-package cna-azure-network-engine`), dry run of the `regen` step's own script on a scratch clone with `RUNNER_TEMP`, `GITHUB_WORKSPACE`, `LATEST=0.1.0`, `DIST` and `URL` set as the `expect` step would, Docker Desktop 29.9.2 | yes | `Using CPython 3.15.2 interpreter at: /usr/local/bin/python3.15`, `Resolved 52 packages`, `Added cna-azure-network-engine v0.1.0`, exit 0; only `pyproject.toml` and `uv.lock` changed; the `verify` step's inline lock check on that lock against `main`'s: `only cna-azure-network-engine changed, pinned to … with sha256:a609b800…`, exit 0. Not run here: the whole workflow (it runs on `main` only); the proof is the first scheduled or manual run after the merge |
| The `image` job steps again, on a port build and a wheel build (sandbox-only Dockerfile copy as above) | yes | `engine: none interim port … (ENGINE_REF none)` and `engine: 0.1.0 cna-azure-network-engine 0.1.0 (ENGINE_REF 0.1.0)`; `Python 3.14.8`; MIT. The step's comparison, run by hand against the wheel image with the pin changed to 0.2.0, reports the mismatch |
| Full suite after the review round | yes | re-run after the follow-up to #66: port: ruff clean, catalog in sync, 495 passed, 6 skipped (the wheel-only tests), coverage 97.19%; wheel: 41 failed (the same engine differences), 460 passed, nothing skipped, so the new engine-package boundary scans, the runtime import check, the pin check and the hedge-word check pass on the wheel; Playwright 4 passed on each |
| actionlint | **no** | downloading and running it was refused by this session's safety check; not worked around |
| Follow-up to PR #66 (Copilot review 5721501497): `Health.required` names `engine`; the RECORD check reads the RECORD text and allows only the package and its own `.dist-info`; cloud-SDK markers must be exactly one `extra == '<name>'` and evaluate false with no extra on four platforms; the `outcome` file must be byte-exact | yes | the new contract test fails with `engine` removed from `Health.required`; on the wheel, the boundary tests pass (13) and fail for each tampered marker (`extra == 'azure' or sys_platform == 'linux'`, `sys_platform == 'win32'`, `extra != 'azure'`) and each tampered RECORD line (`../../../bin/evil`, `/etc/evil`, `C:\evil`, `other_pkg/x.py`, a foreign `.dist-info`, `cna_azure_network_engine/../../x.py`, a `.pth` file). The old check missed every RECORD case: `Distribution.files` leaves out entries whose file does not exist. The dry run refuses four more `outcome` files (padded, split, no newline, followed by more text); 21 of 21 dry-run cases behave as expected |
| `core-update.yml` on GitHub (scheduled run, App token, bump pull request, its required checks, the auto-merge step) | **no** | cannot be started from this session. Expected on the first scheduled run after merge: a pull request `core: adopt engine 0.1.0 (needs adaptation)` from branch `core-update/engine-v0.1.0`, opened by the App, with this repository's checks starting on it, and no merge: auto-merge is turned on if `CORE_AUTOMERGE` is `true`, but it waits for the required checks, which fail as the compatibility check did (wording updated 2026-10-31 for pull request 68) |
| actionlint, zizmor, CodeQL, gitleaks, dependency-review | **no** | not installed here; the pull request's own checks run what CI runs |

## Run 2026-10-27 (release 0.1.1 published)

Run on GitHub after the owner said yes to the tag ([issue 50](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/issues/50)).
Nothing in the application changed; this records the dry run, the tag and what the registry shows.

| Check | Result |
| --- | --- |
| The gate step of `publish-images.yml` for a manual run, its own shell run with the repository variables set as they are | **Before** [pull request 51](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/51): `push=true` for a manual run on `main`, so a "dry run" could have reached the Docker login. **After**: `push=false` with a notice for anything that is not a `v*` tag; a tag gives `push=true`; a tag with publishing switched off gives `push=false` |
| Publish dry run on `main` at `f2276fcd` (the guard and the release both merged), [run 40501557330](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/40501557330) | success. The build, the in-image boundary check (which asserts the licence label) and the Trivy scan passed; the gate step passed; the Docker login, the push, the attestation and the digest record were skipped |
| Tag `v0.1.1` on that same commit, [publish run 40502052247](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/40502052247) | success: login, push with provenance and SBOM, attestation, digest record |
| Digest in the registry | `sha256:338e0e035d053b918f6840bab6eb5871eb739f4d132a076d9497fec54a162635` for `docker.io/hybridcloudworks/img-ne-lab-addon:v0.1.1` |
| Labels on the published image (`docker buildx imagetools inspect <image> --format '{{json .Image.Config.Labels}}'`) | `org.opencontainers.image.licenses=MIT`, `org.opencontainers.image.version=0.1.1`, `org.opencontainers.image.revision=f2276fcd0ce1d1160807566fc1622bc3e2744e55` |
| `gh attestation verify oci://docker.io/hybridcloudworks/img-ne-lab-addon:v0.1.1 --repo saulpatinojr/HCW-NetworkEyes_AddOn` | passes (exit 0). With `--format json`: the attested subject digest equals the registry digest above, the predicate is SLSA provenance v1, the signer is `.github/workflows/publish-images.yml@refs/tags/v0.1.1` of this repository, and the source commit is the tagged commit. Without a terminal the command prints nothing, so read its exit code or use `--format json` |
| GitHub Release | [v0.1.1](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/releases/tag/v0.1.1) |
| The live lab host | **not changed**: it keeps running the `v0.1.0` image until a website change pins the new digest (the owner said nothing changes on the website for this release) |

The section below records the state when the release was prepared, before the guard, the dry run and the tag.

## Run 2026-10-27 (release 0.1.1 prepared)

This run prepares the version bump only and publishes nothing; the lab application's code is unchanged since 0.1.0
except for `__version__`. "Here" is the owner's Windows workstation: Python 3.14.6 (`.python-version`), uv 0.12.0 (CI uses
0.11.32, which was not run), Docker Desktop with engine 29.9.2 on the local `desktop-linux` context.

| Check | Executed here | Result |
| --- | --- | --- |
| The version in every place that says it: `pyproject.toml`, `uv.lock` (the `hcw-addon-network-assessment` entry), `__version__`, `repository.manifest.json` and the sample output in `docs/operations/runbook.md`; `uv lock --check` | yes | all `0.1.1`; `uv lock --check` exits 0; the lock differs from `main` in that one version line (uv 0.12.0 also rewrote the file's `revision = 5` to `3`; that line was put back by hand) |
| `docs/api/openapi.yaml` `info.version` | not changed | stays `0.1.0`: it versions the API document, no route, field or error code changed, and no test ties it to `__version__` |
| `uv run ruff check . && uv run ruff format --check .` and `uv run python scripts/rules-doc.py --check` | yes | clean (86 files); `docs/rules/catalog.md` in sync (422 lines) |
| `uv run pytest -q --cov=src --cov-report=term-missing --cov-fail-under=85` | yes | 246 passed, coverage 97.99% (gate 85). It includes `test_manifest_version_matches_pyproject` (`pyproject.toml`, `repository.manifest.json` and `__version__` agree) and `test_health_is_flat_and_complete` (the body's `version` and the `X-Addon-Version` header equal `__version__`) |
| Live server on a local port (`NA_ALLOW_NO_TURNSTILE=1`), `GET /api/health`, and the runbook's `curl -sI` | yes | body `"version":"0.1.1"` and header `X-Addon-Version: 0.1.1`; `curl -sI` (a HEAD request) answers `405 Method Not Allowed` but still carries `x-addon-version: 0.1.1`, so the runbook command shows the version |
| `IDENTITY_ENDPOINT=http://169.254.169.254 uv run python -c "import network_assessment.app"` | yes | exit 1, `EditionBoundaryError: refusing to start: identity environment present (IDENTITY_ENDPOINT)` |
| Local image build (`docker build -f infrastructure/docker/Dockerfile --build-arg EDITION=lab -t img-ne-lab-addon:ne50-0.1.1 .`, tag removed afterwards) | yes, local only | exit 0; label `org.opencontainers.image.licenses` = `MIT`; `network_assessment.__version__` in the image = `0.1.1`; `import azure` fails; uid 10001; a read-only container with `--cap-drop ALL` and `no-new-privileges` answered `/api/health` with version `0.1.1` and header `X-Addon-Version: 0.1.1`. This is a local linux image on Docker Desktop, not the CI build: it was not scanned, signed or pushed |
| The website's guide-drift script (`scripts/addons/check-guide-drift.mjs` at the commit `guide-drift.yml` pins, run locally against this guide and the website's `main` at `df91043`) | yes | `in step: 13 fields compared`, exit 0. The guide is not touched by this change (it names no version) |
| Read-only lookups behind the two README corrections: the website catalogue row on `main`, `GET /api/public/addons/network-assessment/status`, Docker Hub's public tag list for `hybridcloudworks/img-ne-lab-addon`, and the repository variable `DOCKERHUB_ENABLED` | yes | row `status: 'available'`; the status route answered `configured: true, reachable: true, version: 0.1.0` (the lab host runs the `v0.1.0` image); tags `v0.1.0`, `0.1.0` and `v0.1.1-rc.1` (plus their `sha-` tags) exist, none newer; `DOCKERHUB_ENABLED` is `true` and `DOCKERHUB_CONNECTION` exists (its value was not read) |
| `pwsh scripts/package-repository.ps1` | yes | wrote the archive (142 files, 0.28 MB); deleted afterwards. `bash scripts/package-repository.sh` was not run here: `zip` is not installed on this workstation (exit 127) |
| Publish dry run on the merged commit (`gh workflow run publish-images.yml --ref main`) | **no** | the second line of "Done when" in issue [50](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/issues/50); it is run after this change merges. Read first: the gate step of this repository's `publish-images.yml` does not check for a `v*` tag (the Cloud Crawler's has since [its pull request 18](https://github.com/saulpatinojr/HCW-CloudCrawler_AddOn/pull/18)) and `DOCKERHUB_ENABLED` is `true`, so a manual run on `main` would go on to the registry login, which the Docker connection (it trusts tags only, `docs/deployment/lab-host.md`) is expected to refuse. That is inferred from the Cloud Crawler's experience, not observed here |
| Trivy scan, push, provenance, SBOM, attestation, digest | **no**, CI on a `v*` tag only | `publish-images.yml`; only a `v*` tag pushes, and `v0.1.1` is the owner's call |
| Playwright e2e, CodeQL, gitleaks, dependency-review, `ci.yml` on the pull request | **no**, CI only | not run here (Playwright is not installed here and no tool was installed); the pull request's own checks cover them |

## Run 2026-10-10 (0.1.0, initial)

Toolchain: Python 3.14.6 (`uv python pin 3.14.6`), uv 0.11.32, Node 26.11.1 (for Playwright only), chromium 1243
(`@playwright/test@1.63.0`). Resolved pins: fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0 (pydantic-core 2.50.0,
starlette 1.7.0, anyio 4.15.1, h11 0.16.0, click 8.5.0, idna 3.20, annotated-types 0.8.0, annotated-doc 0.0.5,
opentelemetry-api 1.45.1, typing-extensions 4.16.0, typing-inspection 0.4.4); dev pytest 9.1.1, pytest-cov 7.1.0,
ruff 0.17.0, httpx 0.28.1, pip-audit 2.10.1; build hatchling 1.32.4. `uv.lock` and `requirements.lock.txt`
(`uv export --format requirements-txt --no-dev --no-emit-project --no-emit-workspace --no-header`; hashes are on by
default) are committed (since 2026-10-16 only `uv.lock`: the image build runs the export, and CI checks
`uv lock --check`); 14 third-party runtime packages, none Azure. Base image
`python:3.14.7-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d` (the website's
pin at authoring, CONTRACT-DECISIONS item 20; `python:3.14.8-slim-trixie` with the website since 2026-10-16, moved
on 2026-10-26 to the website's newer digest `sha256:fbecd461...`).

| Check | Executed here | Result |
|---|---|---|
| `uv python pin 3.14.6 && uv sync` | yes | 51 packages resolved and installed |
| `uv run ruff check . && uv run ruff format --check .` | yes | clean (84 files) |
| `uv run python scripts/rules-doc.py --check` | yes | `docs/rules/catalog.md` in sync (422 lines); 45 rules, 34 evaluated over an export, 11 live-only; every registry text hedge-free |
| `uv run pytest -q --cov=src --cov-report=term-missing --cov-fail-under=85` | yes | 223 tests passed; coverage 98.08% (2,509 statements, 41 missed; gate 85). `__main__.py` is covered only by its subprocess tests, which coverage does not trace |
| `uv run pytest tests/security tests/contract -q` | yes | 17 passed (edition boundary incl. fresh-process refusal, Dockerfile/compose free of host network and Arc mounts, no secrets, content-free logs, OpenAPI two-way, every emitted error code documented) |
| Ported rule tests, registry invariants, sample expectations | yes (part of the suite) | every portable rule fires on the sample at least once (34 ids, 45 findings: critical 3, high 11, medium 19, low 10, informational 2; 11 unknowns; topology `hub_spoke`, 2 hubs, 2 spokes); registry digest pinned to `RULES_VERSION = 2026.10.0`; hedge-free titles, descriptions, remediation and facts asserted through the ported enforcer |
| Live server: `NA_ALLOW_NO_TURNSTILE=1 PORT=8085 uv run python -m network_assessment`, `GET /api/health`, `POST /api/assessments` with `samples/sample-resource-graph.json`, `GET …/report.md`, `GET …/report.json`, `GET …/bundle.zip`, `GET /api/rules`, wrong token, `DELETE`, after-delete, `GET /`, `POST` with the portal CSV | yes | health `ok:true id:network-assessment version:0.1.0 edition:lab rules:{2026.10.0,45,11} model:{lab-1.0.0}`, headers `X-Addon-Id`, `X-Addon-Version`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, CSP with `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Cache-Control: no-store`; 201 with 45 findings / 2 ingestion warnings; report.md 200 (58,195 B); report.json 200 (141,171 B); bundle.zip 200 (314,118 B); rules 45/11; wrong token 404; `{"deleted":true}`; 404 after delete; index 200; portal CSV 201 with 2 findings, 43 unknown rules and the "no properties column" warning. Log lines carried only counts, flags and event names |
| `IDENTITY_ENDPOINT=http://169.254.169.254 uv run python -c "import network_assessment.app"` | yes | exit 1 with `EditionBoundaryError: refusing to start: identity environment present (IDENTITY_ENDPOINT)`; `python -m network_assessment` under `MSI_ENDPOINT` exits 3 with one scrubbed `startup_refused` line |
| `uv run pip-audit -r requirements.lock.txt --strict` | yes | no known vulnerabilities |
| Playwright e2e (`npx playwright test -c tests/e2e/playwright.config.ts`, chromium) | yes | 4 passed: standalone journey (sample, summary tiles and topology, severity and category filters, resource detail drawer, unknowns panel, "What this cannot tell you", copy report, resources tab, download, delete); vendor-name scan; framed pane under the site's sandbox posting `loading, ready, working, ready` to the host origin, dark theme by `?theme=dark`; headers, health and the `invalid_export` answer |
| `bash scripts/package-repository.sh` | yes | `hcw-networkeyes-addon.zip` (264 KB); archive file set equals `git ls-files` (165 entries incl. directories); no excluded path leaked |
| `git status --short \| wc -l` | yes | 30 top-level entries (133 files, all untracked: initial commit pending; the parent commits) |
| `versions.env` vs every `FROM` | locally by the same shell snippet as `ci.yml`; CI | both `FROM` lines equal `BASE_IMAGE@BASE_DIGEST` |
| `requirements.lock.txt` vs `uv export` | yes | identical |
| Docker image build (`infrastructure/docker/Dockerfile`) | **no**, CI only | no daemon here; `publish-images.yml` builds, proves `import azure` fails and the container exits under `IDENTITY_ENDPOINT`, runs the hardened health check, scans with Trivy, and pushes only when `DOCKERHUB_ENABLED` is `true` |
| Trivy scan, SBOM, provenance, attestation | **no**, CI only | as above |
| Human verification against the real siteverify endpoint | **no** | mocked in `tests/unit/test_api.py` and `test_security_modules.py` (success, wrong action, wrong hostname, refusal, unavailable); the real call needs the owner's widget and secret (`docs/deployment/lab-host.md`) |
| Lab-host deployment, Caddy route, website pane | **no** | owner steps and the website PR (Phase 6); the catalogue row stays `coming` until the digest exists |
| `core-update.yml` against a Core release | **yes**, CI | ran for real since this table was first written: it opened the bump pull requests that adopted `engine-v0.1.1` ([#78](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/78)) and `engine-v0.1.2` ([#87](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/87)); `pyproject.toml` carries `# ENGINE_REF 0.1.2` (row updated 2026-11-08) |
| CodeQL, gitleaks, dependency-review | **no**, CI only | `security.yml` |

## Limitations recorded

- Since `pyproject.toml` carries the `# ENGINE_REF` line (the wheel's version since pull request 78), `core-update.yml` is armed: its `pull-request` job opens the bump pull request with a GitHub App token (the HCW Main Admin App: its client ID is the repository variable
  `HCW_MAIN_ADMIN_CLIENT_ID`, its private key the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY`), not `GITHUB_TOKEN`, so the required checks run on the pull request itself. That path is covered by
  `tests/security/test_core_update_app_token.py` (static) and by the dry runs of 2026-10-31; the two-job version was not linted with
  actionlint or zizmor, and it has not yet opened a real bump pull request here. To prove the credential on a day with no release to adopt:
  `gh workflow run core-update.yml -R saulpatinojr/HCW-NetworkEyes_AddOn --ref main -f probe=true`.
  The App key lives only as the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY` and is never printed. To rotate it,
  generate a new private key on the settings page of the App (https://github.com/settings/apps), replace the secret in every repository that holds the key (this one:
  https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/settings/secrets/actions; the App is installed on the four
  add-on repositories, so check the other three; HCW-CloudCrawler_App and HCW-CloudAssessor_App, where the owner decided on 2026-11-04
  to install it too, hold a separate key as Dependabot secrets and are rotated on their own), then delete the old key on the settings page of the App.
  The settings page can hold several keys, so a separate key per repository lets you revoke one without
  touching the others.
  **Accepted risk, so nobody has to rediscover it.** A repository secret can be read by any workflow that runs from a branch
  someone with write access can push, so `base-update.yml` is a second reader of the key beside `core-update.yml` (both can
  be started by hand with `workflow_dispatch`), and the base-update proof depends on that: it runs the workflow from a
  throwaway branch. As of 2026-10-27, only the owner can push here. The App is installed on the four add-on repositories (and, since 2026-11-05, on HCW-CloudCrawler_App and HCW-CloudAssessor_App, as decided on 2026-11-04; its first run there is the proof tracked on HCW-CloudCrawler_App issue #70), and both
  workflows ask the token action for this repository only (`repositories: ${{ github.repository }}`) with Contents and Pull
  requests write; a token lasts one hour. A modified workflow on another branch could ask for more: the limit is then whatever
  the App was granted when it was installed (that list is on the App's settings page, https://github.com/settings/apps, and is
  not repeated here because a session cannot read it), which is why the key is a risk. The owner decided on 2026-10-26 to leave
  the key as a repository secret ([HCW-HybridCloudWorks#1410](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1410));
  the stronger options (an environment limited to `main`, or a separate App installation for each repository) can be reopened
  if the key is ever suspected leaked. A separate key for each repository on the same App is not one of them: it helps rotation
  (one key can be revoked without touching the others) but it does not shrink what a stolen key can reach, because every key
  authenticates the same App, and that App is installed on all four add-on repositories and, since 2026-11-05, on HCW-CloudCrawler_App and HCW-CloudAssessor_App too
  (their lockfile workflow pushes with it, HCW-CloudCrawler_App issue #70). A stolen key could then reach those
  two repositories as well, though `main` in both still needs a pull request with an approval of its latest push. An environment limited to `main` would
  also stop the base-update proof, which needs a run from a branch.
  Auto-merge of a
  bump (any bump since pull request 68; it then waits for the required checks) needs the repository setting "Allow auto-merge" (on 2026-10-26 UTC); with it off, `core-update` warns
  and leaves the pull request for a person to merge.
- The engine wheel is the only engine (ADR-0006): without it installed the lab does not start (`EngineNotInstalled`).
  The comparison of the wheel's normalizer with the lab's own went with the lab's normalizer; the normalised result
  of the samples is still pinned by `tests/unit/test_normalize.py`, run against the wheel. An engine fault is fixed
  upstream and arrives as the next release; it is not patched here.
- An export shows configuration only: metrics, diagnostic settings, attacks in progress, BGP state, effective routes
  and NSG rules, private DNS resolution, Defender assessments and cost are `unknown` by design (11 live-only rules
  reported in `unknowns[]`; the panel and `report.md` say so).
- AZ-NET-006 and AZ-NET-014 answer `unknown` for the whole export when it carries no `networkwatchers/flowlogs` rows;
  AZ-NET-030 answers `unknown` when gateways exist but no `connections` rows do. Flow logs targeting a VNet, a subnet
  or an NSG mark the VNet; NIC-level NSGs and flow logs are not evaluated (`networkinterfaces` rows are counted only).
- AZ-NET-011 counts the `ipConfigurations` the export lists on a subnet against the prefix size minus the five
  reserved addresses; delegated and private-endpoint subnets report their allocations the same way, and IPv6
  prefixes are not counted.
- AZ-NET-012 follows the Core's spoke definition (a VNet whose peering uses remote gateways or allows forwarded
  traffic), so a hub whose peerings allow forwarded traffic is also checked; the sample shows this on the hub's
  application-gateway subnet.
- The topology classifier marks any VNet with `allowGatewayTransit` as a hub (the engine's semantics, first ported here, now the wheel's); the sample's
  `hcw-sample-vnet-legacy` is therefore a hub with no gateway, which is also what AZ-NET-005 reports.
- The portal "All resources" CSV maps the display names of 22 network types to ARM types; other display names stay
  as written and are counted, not evaluated. Only the two count-based rules (AZ-NET-004, AZ-NET-033) run on it.
- Resources outside `microsoft.network/` are counted in `byType` and ignored with one warning; `localnetworkgateways`,
  `networkwatchers`, `ddosprotectionplans` and other unmapped network types are counted and listed in the warnings.
- Every `learn_url` is the most plausible page on `learn.microsoft.com` as of 2026-10-10 and is marked `[VERIFY]`
  until the owner confirms it; every framework reference is `[VERIFY]` and `[REVIEW REQUIRED]` (legal/compliance);
  the Basic SKU retirement date (2025-09-30) named in AZ-NET-026/027 is `[VERIFY]`; the ported Core code whose MIT
  relicensing was `[REVIEW REQUIRED]` was deleted on 2026-11-08 (`NOTICE`, ADR-0006); the `downloads` sandbox capability is
  `[REVIEW REQUIRED]` on the website side; the base-image digest is `[VERIFY]` at the first image build; numbering the
  zone-redundancy rules AZ-BCDR-006/007 (not AZ-NET-02x) and lowering AZ-NET-032/033 to MEDIUM/LOW are flagged for
  the owner.
- The 5 MB cap stops reading at the limit and answers 413; the socket close past the limit is uvicorn's behaviour on an
  unread body and was observed only through the test client, not with a raw socket.
- The lab application is copied into the image as a source tree rather than built as a wheel (no build backend in the
  image); `importlib.metadata` therefore does not know it, and the version comes from `__version__` (asserted equal to
  `pyproject.toml` and `repository.manifest.json` by a test).
- starlette 1.7 prefers `httpx2` for its test client; this edition pins `httpx` (the brief) and mutes that one
  deprecation notice in `pyproject.toml`.
- `pyproject.toml` is a single project, not a uv workspace with an engine member as the sibling has: the engine is a
  pinned wheel dependency, and the interim port that used to live under `src/network_assessment/{model,rules,classify}`
  was deleted (ADR-0006); the brief's validation command `import network_assessment.api.app` is therefore
  `import network_assessment.app` here (the sibling's module layout, ADR-0002).
- `base-update.yml` moves the base image pin to the website's pin by opening a pull request, with the same HCW Main Admin App credential as
  `core-update.yml` (so `core-update.yml`'s probe run also proves the credential here). The workflow, `scripts/follow_website_base.py` and the three
  test files (`tests/unit/test_follow_website_base.py`, `tests/unit/test_base_image_pin.py`, `tests/security/test_base_update_workflow.py`)
  were copied byte for byte from the Cloud Assessor add-on (merged there in
  [pull request 49](https://github.com/saulpatinojr/HCW-CloudAssessor_AddOn/pull/49)). That version was proved live there on 2026-10-27:
  [run 40488729010](https://github.com/saulpatinojr/HCW-CloudAssessor_AddOn/actions/runs/40488729010) opened the pull request and its checks ran,
  [run 40490178354](https://github.com/saulpatinojr/HCW-CloudAssessor_AddOn/actions/runs/40490178354) left a person's commit alone, and
  [run 40493622020](https://github.com/saulpatinojr/HCW-CloudAssessor_AddOn/actions/runs/40493622020) closed a pull request that was no longer needed
  (recorded in Cloud Assessor's [pull request 59](https://github.com/saulpatinojr/HCW-CloudAssessor_AddOn/pull/59)).
  **Verified here, on 2026-10-27, on a workstation:** the five files are identical to Cloud Assessor `main` (checked by hash); the three test files pass
  here (167 passed) and so does the whole suite (413 passed, coverage 97.99 percent, gate 85); `ruff check`, `ruff format --check`,
  `uv lock --check` and `scripts/rules-doc.py --check` pass; `tests/unit/test_base_image_pin.py` was seen to fail when the digest in `versions.env`
  was changed, and again when one `FROM` line was changed, and to pass once both were put back; `actionlint` 1.7.12 is clean on the workflow once the
  runner label `ubuntu-26.04` is declared in a temporary config file (it does not know that label); the runbook's PowerShell blocks parse in
  Windows PowerShell 5.1.
  **Not verified in this repository until its own proof has run** (the steps are in `docs/operations/runbook.md`, "Keeping the base image on the
  website's pin"; the workflow cannot be started before it is on `main`): a first run of the workflow here; the scheduled trigger (07:37 UTC); the
  token step and `create-pull-request` pushing and opening the pull request here; the registry check on the runner's own `docker buildx`; the
  commit identity (`<id>+<slug>[bot]@users.noreply.github.com`); the closing of an obsolete pull request; the runner's own `python3` version (the
  script is written for Python 3.9 and later and a test guards that); and whether the ruleset "Protect main" option "require extra approval for
  unattributed changes" asks for an extra approval on a pull request into `main` (the pull requests of the Cloud Assessor proof went into a
  throwaway branch, not into `main`; this ruleset asks for no approvals otherwise, so no extra approval is expected, but that is an expectation,
  not something seen). Scheduled workflows in a public repository are switched off by GitHub after 60 days without repository activity. That
  switches off `base-update` and the weekly `base-follows-website` job together, so after a quiet spell the weekly job is not an independent
  second check. It is also not a full second check at any time: it compares only the image and its digest, so if the website changes only
  `BASE_PYTHON_VERSION` to another minor line, `base-update` refuses and goes red while the weekly job stays green. How to see whether either
  workflow has been switched off, and how to switch them back on, is in `docs/operations/runbook.md`, "If the daily run goes quiet"; failed
  `base-update` runs should be watched on their own ("When the run is red").
