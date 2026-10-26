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
  touching the others. Auto-merge of a
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
