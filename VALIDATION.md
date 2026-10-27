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

- When it is not inert, `core-update.yml` opens the pull request with a GitHub App token (the HCW Main Admin App: its client ID is the repository variable
  `HCW_MAIN_ADMIN_CLIENT_ID`, its private key the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY`), not `GITHUB_TOKEN`, so the required checks run on the pull request itself. That path is covered by
  `tests/security/test_core_update_app_token.py` (static) and was linted with actionlint and zizmor; it has not yet opened
  a real bump pull request here. To prove the credential while the workflow is inert:
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
  throwaway branch. Today only the owner can push here. The App is installed on the four add-on repositories, and both
  workflows ask the token action for this repository only (`repositories: ${{ github.repository }}`) with Contents and Pull
  requests write; a token lasts one hour. A modified workflow on another branch could ask for more: the limit is then whatever
  the App was granted when it was installed (that list is on the App's settings page, https://github.com/settings/apps, and is
  not repeated here because a session cannot read it), which is why the key is a risk. The owner decided on 2026-10-26 to leave
  the key as a repository secret ([HCW-HybridCloudWorks#1410](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1410));
  the stronger options (an environment limited to `main`, one key per repository) can be reopened if the key is ever suspected
  leaked. An environment limited to `main` would also stop the base-update proof, which needs a run from a branch.
  Auto-merge of a
  compatible bump needs the repository setting "Allow auto-merge" (on 2026-10-26 UTC); with it off, `core-update` warns
  and leaves the pull request for a person to merge.
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
