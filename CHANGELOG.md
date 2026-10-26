# Changelog

All notable changes to this repository are recorded here. The format follows Keep a Changelog; versions are semver tags.

## [Unreleased] — 0.1.0

### Changed
- The lab image repository on Docker Hub is renamed from `hybridcloudworks/hcw-addon-network-assessment` to `hybridcloudworks/img-ne-lab-addon` (owner naming convention `img-<short name>-<job>-<type>`, 2026-10-25), and its tag is now the full release tag (`v0.1.0`, not `0.1.0`). `publish-images.yml` (`IMAGE`, the tag, the image title label), the local `:dev` build tag, the README and the deployment and integration documents follow. The container name on the lab host (`hcw-addon-network-assessment`) is **not** changed: the website's host role owns it. Nothing is published by this change; the next `v*` tag pushes to the new name once the Docker OIDC connection allows it (`docs/deployment/lab-host.md`, step 4).
- Hardening: the last step of `publish-images.yml` printed the release version straight into a shell command (`echo "image_tag: ${{ steps.version.outputs.version }}"`). The version comes from the pushed tag's name, so a crafted tag name could inject a command. It now reaches the shell through the environment variable `IMAGE_TAG` and is printed as `"${IMAGE_TAG}"`. This was already present before the rename; only people with write access can push tags.
- `docs/website-integration/integration-guide.md` follows the website after hybridcloudworks.com#1359 (issues #1353 and #1354, owner decisions of 2026-10-24): the row now holds `downloads` and `clipboard-write` (it held `navigate` and `downloads`), the frame address carries `?theme=dark|light` read once from the site's theme, the clipboard grant is write only, and the row copy is taken from website commit b0cf0055.
- `docs/website-integration/integration-guide.md` now follows the website's real catalogue row. The row pasted into it was
  written before the row shipped and had drifted: 6 of its 10 fields differed from the website's (title, summary, pane
  path, technology, status and capabilities, plus the `comingSince` and `comingReason` fields). The block is now a copy
  of the website's current row, with the website commit it came from, and says the website is the authority. The guide
  also says that the site frames `origin + panePath` with no `?theme=` parameter (the pane still honours one), and that
  the site grants `navigate` and `downloads` where this AddOn asked for `downloads` and `clipboard`; the owner confirms
  whether that is intended. Compared field by field with a script on 2026-10-24: 0 of 10 now differ.
- `.github/dependabot.yml` groups `pydantic` and `pydantic-core` so they arrive in one pull request. pydantic requires one exact `pydantic-core`, so a `pydantic-core` bump on its own cannot resolve; the same failure closed the App repository's Dependabot pull requests.
- Dependency updates pass CI as Dependabot opens them. Its `pip` updater rewrote `pyproject.toml` and the committed
  `requirements.lock.txt` but never `uv.lock`, so every one of its pull requests failed the export check (#16 to #19).
  `.github/dependabot.yml` now uses the `uv` ecosystem, which moves `pyproject.toml` and `uv.lock` together. The
  committed export is gone: the image's build stage runs `uv export --frozen` from `uv.lock` with the uv CI uses, by
  digest, and still installs with `pip --require-hashes --no-deps`; uv never reaches the lab stage. CI checks
  `uv lock --check` and that the Dockerfile's uv is `UV_VERSION`; `pip-audit` audits the same export.
- Base image `python:3.14.8-slim-trixie` by digest, the website's current pin (CONTRACT-DECISIONS item 20). There is
  no docker Dependabot entry: the base follows the website, and the uv image follows `UV_VERSION`. CI builds the
  image on every pull request, resolves the uv digest for `UV_VERSION` rather than trusting any digest, and a weekly
  job flags the base drifting from the website's pin.
- The base image digest follows the website's current pin again (`python:3.14.8-slim-trixie@sha256:fbecd461...`, same
  tag, newer build; `versions.env` and both `FROM` lines). The website rebuilt on it on 2026-10-21; `security.yml`'s
  `base-follows-website` job, which runs on `main` and weekly only, had been red on `main` since its first run after
  that (2026-10-24). An image built from the next tag uses the current base; a tag already published keeps the base
  it was built on.
- Repository hygiene: `.github/dependabot.yml` groups GitHub Actions updates under `all-actions` and removes the unused `/tests/e2e` npm entry; `infrastructure/docker/Dockerfile`, `README.md`, and `CLAUDE.md` updated to match `HCW-NetworkEyes_App` and `ADR-0005`.
- README: a "where to try it" paragraph for new visitors; the diagram says the engine wheel is attached to each `engine-v*` release of the App. `core-update.yml`'s checkout no longer persists credentials (two Authorization headers made GitHub answer `400` to `create-pull-request`'s push in the Migrate App's `rules-refresh`).
- **Upstream is `saulpatinojr/HCW-NetworkEyes_App`** (owner decision 2026-10-10: the Core lineage was merged back into the App, which now holds the engine package and its `engine-v*` releases). `core-update.yml` watches that repository and pins the engine as the GitHub Release wheel asset by URL, so `uv lock` records its sha256 and the image's `pip install --require-hashes` keeps verifying it (a git+https pin cannot be hash-checked); no PyPI step is needed for adoption. Provenance headers, `PROVENANCE.md`, the governance files and the docs name the App; ADR-0001 and ADR-0004 carry an amendment note.

### Added
- `.github/workflows/guide-drift.yml` switches on the website's check that this repository's integration guide still says what the website says (website issue saulpatinojr/HCW-HybridCloudWorks#1356). It calls a reusable workflow (a workflow that another repository can call, like a function) from the website repository, pinned to a full commit, and compares the catalogue row pasted into `docs/website-integration/integration-guide.md` with the website's row for `network-assessment`, field by field. It runs on pull requests that touch the guide or this workflow, every Monday at 06:35 UTC and on demand. It holds no secret and has `contents: read` only. To switch it off, delete the file. How to read a failure: https://github.com/saulpatinojr/HCW-HybridCloudWorks/blob/main/docs/runbooks/addon-guide-drift.md
- **`docs/whats-new-upstream.md`**: the running record of what changed in the App and what this edition has to do about it, with the state of the engine release (`engine-v0.1.0`, published 2026-10-12, not adopted yet) and the adoption steps. `CLAUDE.md`, `AGENTS.md`, `README.md`, `PROVENANCE.md`, `VALIDATION.md` and `infrastructure/README.md` no longer say the wheel is still to be published. Listed in `repository.manifest.json`.
- **Always-on guided workspace handoff (ADR-0005):** `POST /api/assessments/{assessment_id}/workspace` (`202 Accepted`) issues a single-use, 10-minute `x-bundle-token` (`AssessmentStore.issue_bundle_token` / `redeem_bundle_token`) scoped to `GET /api/assessments/{assessment_id}/bundle.zip` and returns a workspace launch descriptor (`CoderWorkspaceProvider` in `src/network_assessment/workspace.py`). Supports both direct upstream API provisioning (when `CODER_SESSION_TOKEN` is set) and browser-session auto-create deep links (`https://coder.lab.hybridcloudworks.com/templates/na-guided-lab/workspace?mode=auto&...` by default). `/api/health` and `/api/config` report `"workspace": "coder"` and `"workspace"` in `CAPABILITIES`. Added `#open-workspace` ("Open in lab workspace") to `web/index.html` and `web/app.js`, the ADR-0032 / LAB-5 hardened Linux container Coder template `infrastructure/coder/template/main.tf` (`tcp://coder-docker-proxy:2375`, `user = "65534:65534"`, `HOME = "/tmp/home"`, `module "code-server"` with `subdomain = true`, `/usr/local/libexec/hcw-boot/hcw-boot network-assessment` + `python3 -m zipfile -e`), `.github/workflows/iac-validate.yml`, `.github/workflows/coder-template.yml`, `docs/deployment/coder.md`, and `docs/adr/ADR-0005-always-on-guided-workspace-handoff.md` (with appliance team handoff notes; core engine under `src/network_assessment/{model,rules,classify}` untouched).
- Code scanning: the e2e host page accepts only a loopback `?addon=` origin for the frame and the message filter, and the unit test asserts the exact `script-src` and `frame-src` source lists instead of a substring (closes the three CodeQL alerts raised on #5; test and harness code only, no runtime change).
- Interim ported engine (ADR-0001, `PROVENANCE.md`) from `saulpatinojr/HCW-NetworkEyes_App` at `5d3b914`: the
  observed-state enforcer (verbatim), the trimmed findings model (`ObservedState.state`, `remediation`, `learn_url`,
  `rule_version`), the lab topology model `lab-1.0.0` (26 Azure classes plus `AzureFirewallPolicy`,
  `AppGatewayWafPolicy`, `FlowLog`), the topology classifier, the traffic-direction taxonomy and the framework
  mappings as data.
- Rule registry (`@rule`, `RULES`, `RULES_VERSION = "2026.10.0"`, `evaluate()` with `rule_id:resource_id` dedup and the
  enforcer on every fact): AZ-NET-001..007, 011 (re-derived from `ipConfigurations`), 012, 014, 018 ported from Engine A;
  AZ-NET-020..033 ported from Engine B as typed rules; AZ-BCDR-001..005 ported plus 006/007; AZ-COST-001/004 ported
  without the price table; AZ-NET-008/009/010/013/015/016/017/019 and AZ-COST-002/003/005 registered live-only and
  reported in `unknowns[]`. `docs/rules/catalog.md` generated by `scripts/rules-doc.py` with a CI drift check;
  `GET /api/rules` serialises the registry.
- Ingestion: JSON array or `az graph query` envelope (BOM strip, paged warning), Resource Graph Explorer CSV with JSON
  cells, the portal "All resources" CSV accepted with the "no properties column" warning (property rules answer
  unknown); 5 MB / 5,000-row caps; `invalid_export` for anything that is not an export; the normalizer maps ~20
  `microsoft.network/*` types onto the model, resolves references by id within the export, warns on unresolved ones,
  counts network interfaces and lists unmapped types.
- Lab application `src/network_assessment` 0.1.0 (FastAPI 0.143.0, uvicorn 0.54.0, pydantic 2.14.0): `NA_*` settings
  (numeric settings bounded by `MAX_SETTING`), import-time edition guard, in-memory store, human verification with
  `action` echo and `NA_PUBLIC_HOST` hostname binding, fail-closed posture (`NA_ALLOW_NO_TURNSTILE=1` local only),
  security headers with configurable `frame-ancestors`, exact-origin CORS, streamed body cap, per-client token bucket
  (`NA_TRUST_PROXY` for `X-Forwarded-For`), concurrency bound (`503 overloaded`), content-free JSON logs, the flat
  `/api/health` envelope with `rules`, `model` and `limits`, and the documented route set with the error envelope.
- Outputs: summary (counts, topology pattern, findings by severity, unknown rules, versions), `findings[]`,
  `resources[]` with the facts the rules read, `unknowns[]`, `report.md`, `report.json`, `bundle.zip` (README.md,
  report.md, findings.json, topology.json, summary.json, rules.json, NOT-FOR-PRODUCTION.md).
- Vanilla pane (`web/`) with the HCW theme tokens, `?theme=` selection, the `hcw-addon` message bridge
  (`loading | ready | working | unavailable`), upload preview, summary tiles and topology pattern, findings table with
  severity and category filters, resource detail drawer, unknowns panel, "What this cannot tell you" panel, report and
  resources tabs, bundle download, "Copy report" fallback, immediate delete and the expiry line.
- Samples (48 fictional rows in two subscriptions, three export shapes) designed so every portable rule fires; results
  pinned in `tests/unit/test_sample_expectations.py`; unit (incl. ported rule tests), contract (OpenAPI two-way),
  security (edition boundary, no secrets, content-free logs), manifest/provenance and Playwright suites.
- Docs (website integration, routes, API, lab host, appliance pointer, runbook, threat model incl. the host identity
  endpoint, user guide with the owner-pasteable export commands, bundle, generated rule catalog, ADR-0001..0004),
  hardened two-stage Dockerfile on the website's base-image digest, local compose, SHA-pinned `ci`, `security`,
  `publish-images` (Docker Hub by OIDC, Trivy before push, image-level boundary check) and inert `core-update`
  (watches the Core's `engine-v*` releases) workflows, Dependabot, CODEOWNERS, PR template.
