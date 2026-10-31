# Validation

What was executed for this edition and what was not, per run. "Here" is the authoring container (no Docker daemon, PyPI
and the Playwright CDN reachable through a proxy). Dates are the run date.

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
| `core-update.yml` against a Core release | **no** | inert: the App published `cna-azure-network-engine` as `engine-v0.1.0` on 2026-10-12, but `pyproject.toml` has no `ENGINE_REF` line yet, so the comparison step exits cleanly (adoption steps: `docs/whats-new-upstream.md`) |
| CodeQL, gitleaks, dependency-review | **no**, CI only | `security.yml` |

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
| The compatibility check on that bump (`uv sync --frozen`, `ruff check`, `rules-doc.py --check`, `pytest -q`) | yes | ruff clean; `rules-doc.py --check` fails (the hedge word); `pytest`: 41 failed, 428 passed. Every failure is one of the five engine differences: 35 rule-text cases, 3 evidence-reference cases, the report hedge check, and the two pinned sample expectations (AZ-NET-007 fires twice and AZ-NET-025 not at all). The lab's own adaptations pass on the wheel: normalizer parity on all three samples, the registry digest, live-only rules in `unknowns[]`, the API and the edition boundary. So the real bump will be labelled `needs-adaptation` and will not auto-merge |
| The browser suite on that bump | yes | 4 passed on the wheel |
| The `image` job's steps of `ci.yml`, on a port build and on a wheel build | yes, with a sandbox-only Dockerfile copy | The committed Dockerfile cannot download packages inside a build here (the proxy's certificate is not in the build container; the unchanged port build fails the same way). A scratch copy that adds only the proxy's CA bundle to the build stage (verification stays on) built both: `pip install --require-hashes` installed the wheel from the lock; no cloud SDK in `/install`; `engine: interim port …` and `engine: cna-azure-network-engine 0.1.0`; `image python: Python 3.14.8 (BASE_PYTHON_VERSION=3.14.8)`; licence label MIT |
| The new Python-version check against a wrong and a missing `BASE_PYTHON_VERSION` | yes | exit 1 with `the built image runs 'Python 3.14.8', but BASE_PYTHON_VERSION is 3.14.9`, and exit 1 with `BASE_PYTHON_VERSION is missing`; exit 0 with the real file |
| The rewritten manifest check of `test_edition_boundary.py` against a lock with a cloud SDK | yes | fails for a locked `azure-identity` package and for an `azure-identity` requirement without an extra marker; passes on the bump's lock, whose only Azure names are the engine's `[azure]` extra metadata |
| Review round on PR #66: the two-job `core-update.yml`, dry run from the workflow's own step scripts (`bump`: asset, pin and stage; `pull-request`: expect and verify), with a stand-in for the two read-only `gh api` calls | yes | Asset selection: the `cna_` wheel among a tarball or a foreign wheel is chosen; no known wheel, two known wheels, or only a signature file fails. Verify: the genuine artifact passes with outcome `failure` and with `success` (the outcome sets only the label); refused with a message for each of: outcome not one word, an extra file, a symlink, a new dependency in `pyproject.toml`, another URL, another changed line, another package's hash changed in `uv.lock`, a new locked package, the engine wheel without a sha256, the engine pulling in a new dependency, a control character in the catalog, the catalog heading gone. The dry run also found that the workflow's uv 0.11.32 writes `revision = 3` where `main`'s lock says `5`; the verifier allows that one header field to differ (an integer), nothing else |
| Second review round: the pull-request job regenerates `pyproject.toml` and `uv.lock` itself (`uv lock --no-build`) and requires the artifact's copies to be byte-identical; dry run as above, with the local uv 0.11.32 standing in for the binary the job copies out of the digest-pinned uv image (no image was pulled and no external binary run here) | yes | `uv lock --no-build` ran no build backend and gave a lock byte-identical to the bump job's; the genuine artifact passes; every earlier tampered case is still refused, and three more are: another sha256 for the engine wheel in a structurally valid lock (which the structural check alone would have accepted), an extra `pyproject.toml` line (another package index), and a `<script>` tag in the catalog |
| The new pin check (`test_the_engine_that_runs_is_the_one_pyproject_pins`) | yes | passes on the port (`none`) and on the wheel (`0.1.0`); fails for "port installed, pin says 0.1.0", "wheel installed, pin says none" and "wheel 0.1.0 installed, pin says 0.2.0" |
| The `image` job steps again, on a port build and a wheel build (sandbox-only Dockerfile copy as above) | yes | `engine: none interim port … (ENGINE_REF none)` and `engine: 0.1.0 cna-azure-network-engine 0.1.0 (ENGINE_REF 0.1.0)`; `Python 3.14.8`; MIT. The step's comparison, run by hand against the wheel image with the pin changed to 0.2.0, reports the mismatch |
| Full suite after the review round | yes | re-run after the follow-up to #66: port: ruff clean, catalog in sync, 495 passed, 6 skipped (the wheel-only tests), coverage 97.19%; wheel: 41 failed (the same engine differences), 460 passed, nothing skipped, so the new engine-package boundary scans, the runtime import check, the pin check and the hedge-word check pass on the wheel; Playwright 4 passed on each |
| actionlint | **no** | downloading and running it was refused by this session's safety check; not worked around |
| Follow-up to PR #66 (Copilot review 5721501497): `Health.required` names `engine`; the RECORD check reads the RECORD text and allows only the package and its own `.dist-info`; cloud-SDK markers must be exactly one `extra == '<name>'` and evaluate false with no extra on four platforms; the `outcome` file must be byte-exact | yes | the new contract test fails with `engine` removed from `Health.required`; on the wheel, the boundary tests pass (13) and fail for each tampered marker (`extra == 'azure' or sys_platform == 'linux'`, `sys_platform == 'win32'`, `extra != 'azure'`) and each tampered RECORD line (`../../../bin/evil`, `/etc/evil`, `C:\evil`, `other_pkg/x.py`, a foreign `.dist-info`, `cna_azure_network_engine/../../x.py`, a `.pth` file). The old check missed every RECORD case: `Distribution.files` leaves out entries whose file does not exist. The dry run refuses four more `outcome` files (padded, split, no newline, followed by more text); 21 of 21 dry-run cases behave as expected |
| `core-update.yml` on GitHub (scheduled run, App token, bump pull request, its required checks, the auto-merge step) | **no** | cannot be started from this session. Expected on the first scheduled run after merge: a pull request `core: adopt engine 0.1.0 (needs adaptation)` from branch `core-update/engine-v0.1.0`, opened by the App, with this repository's checks starting on it, and no auto-merge (the compatibility check fails) |
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

## Limitations recorded

- Since `pyproject.toml` carries the `# ENGINE_REF none` marker, `core-update.yml` is armed: its `pull-request` job opens the bump pull request with a GitHub App token (the HCW Main Admin App: its client ID is the repository variable
  `HCW_MAIN_ADMIN_CLIENT_ID`, its private key the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY`), not `GITHUB_TOKEN`, so the required checks run on the pull request itself. That path is covered by
  `tests/security/test_core_update_app_token.py` (static) and by the dry runs of 2026-10-31; the two-job version was not linted with
  actionlint or zizmor, and it has not yet opened a real bump pull request here. To prove the credential on a day with no release to adopt:
  `gh workflow run core-update.yml -R saulpatinojr/HCW-NetworkEyes_AddOn --ref main -f probe=true`.
  The App key lives only as the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY` and is never printed. To rotate it,
  generate a new private key on the settings page of the App (https://github.com/settings/apps), replace the secret in every repository that holds the key (this one:
  https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/settings/secrets/actions; the App is installed on the four
  add-on repositories, so check the other three), then delete the old key on the settings page of the App.
  The settings page can hold several keys, so a separate key per repository lets you revoke one without
  touching the others.
  **Accepted risk, so nobody has to rediscover it.** A repository secret can be read by any workflow that runs from a branch
  someone with write access can push, so `base-update.yml` is a second reader of the key beside `core-update.yml` (both can
  be started by hand with `workflow_dispatch`), and the base-update proof depends on that: it runs the workflow from a
  throwaway branch. As of 2026-10-27, only the owner can push here. The App is installed on the four add-on repositories, and both
  workflows ask the token action for this repository only (`repositories: ${{ github.repository }}`) with Contents and Pull
  requests write; a token lasts one hour. A modified workflow on another branch could ask for more: the limit is then whatever
  the App was granted when it was installed (that list is on the App's settings page, https://github.com/settings/apps, and is
  not repeated here because a session cannot read it), which is why the key is a risk. The owner decided on 2026-10-26 to leave
  the key as a repository secret ([HCW-HybridCloudWorks#1410](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1410));
  the stronger options (an environment limited to `main`, or a separate App installation for each repository) can be reopened
  if the key is ever suspected leaked. A separate key for each repository on the same App is not one of them: it helps rotation
  (one key can be revoked without touching the others) but it does not shrink what a stolen key can reach, because every key
  authenticates the same App, and that App is installed on all four add-on repositories. An environment limited to `main` would
  also stop the base-update proof, which needs a run from a branch.
  Auto-merge of a
  compatible bump needs the repository setting "Allow auto-merge" (on 2026-10-26 UTC); with it off, `core-update` warns
  and leaves the pull request for a person to merge.
- The engine wheel `engine-v0.1.0` is not compatible with this edition yet (five differences in the engine, listed in
  `docs/whats-new-upstream.md`). The bump pull request for it is expected to stay `needs-adaptation` until the App
  releases a fix; it is not merged, and the engine is not patched here.
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
- The topology classifier marks any VNet with `allowGatewayTransit` as a hub (ported semantics); the sample's
  `hcw-sample-vnet-legacy` is therefore a hub with no gateway, which is also what AZ-NET-005 reports.
- The portal "All resources" CSV maps the display names of 22 network types to ARM types; other display names stay
  as written and are counted, not evaluated. Only the two count-based rules (AZ-NET-004, AZ-NET-033) run on it.
- Resources outside `microsoft.network/` are counted in `byType` and ignored with one warning; `localnetworkgateways`,
  `networkwatchers`, `ddosprotectionplans` and other unmapped network types are counted and listed in the warnings.
- Every `learn_url` is the most plausible page on `learn.microsoft.com` as of 2026-10-10 and is marked `[VERIFY]`
  until the owner confirms it; every framework reference is `[VERIFY]` and `[REVIEW REQUIRED]` (legal/compliance);
  the Basic SKU retirement date (2025-09-30) named in AZ-NET-026/027 is `[VERIFY]`; the MIT relicensing of ported Core
  code (labelled Proprietary at `5d3b914`) is `[REVIEW REQUIRED]` (`NOTICE`); the `downloads` sandbox capability is
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
- `pyproject.toml` is a single project, not a uv workspace with an engine member as the sibling has: the ported engine
  lives under `src/network_assessment/{model,rules,classify}` and is deleted, not handed upstream, once the Core's
  wheel exists (ADR-0001); the brief's validation command `import network_assessment.api.app` is therefore
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
