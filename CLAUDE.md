# CLAUDE.md — working agreement for Claude Code in this repository

This is `saulpatinojr/HCW-NetworkEyes_AddOn`, the **lab edition** of the Network Assessment (AddOn id
`network-assessment`, site route `/tools/network-assessment`, origin `https://network-assessment.lab.hybridcloudworks.com`):
a Python 3.15 FastAPI application that evaluates an uploaded Azure Resource Graph export of `microsoft.network/*` rows
against typed network rules, a vanilla pane the website frames, fictional samples, docs, a hardened Dockerfile and
SHA-pinned workflows. The engine is the App's released wheel, `network-assessment-azure-engine` (from
`saulpatinojr/HCW-NetworkEyes_App`), pinned in `pyproject.toml` by URL on the `# ENGINE_REF` line and by sha256 in
`uv.lock`; `core-update.yml` opens the bump pull request for each new `engine-v*` release. `src/network_assessment/engine.py`
is the only place lab code reaches it, and it refuses to start without the wheel (no fallback). The interim port that
used to live under `src/network_assessment/{model,rules,classify}` was deleted on 2026-11-08 (ADR-0006, which supersedes
the interim part of ADR-0001); engine changes are made upstream and arrive as a release, never patched here.
**Read `docs/whats-new-upstream.md` before changing behaviour here, and update it when you adopt an upstream change.**

- Run `uv sync`, then `uv run ruff check . && uv run ruff format --check .`, `uv run python scripts/rules-doc.py --check`
  and `uv run pytest -q --cov=src` before claiming anything works; `make e2e` for anything touching the pane or the API.
  Never claim a check passed that you did not run.
- Never weaken: the lab's inability to construct an Azure credential (no cloud SDK; `edition.py` refuses to start under
  `IDENTITY_ENDPOINT`/`MSI_ENDPOINT`/`AZURE_CLIENT_SECRET`/`AZURE_FEDERATED_TOKEN_FILE`/`AZURE_CLIENT_ID`/`AZURE_TENANT_ID`;
  `tests/security/test_edition_boundary.py`); fail-closed human verification (uploads answer 503 without a secret unless
  `NA_ALLOW_NO_TURNSTILE=1`, local only; `action` and, when `NA_PUBLIC_HOST` is set, `hostname` are checked); owner-token
  isolation (hashed, constant-time, 404 for foreign ids); the 5 MB / 5,000-row / 200-item / 120-minute limits;
  exact-origin CORS; the content-free log writer; the "not production" and "no cloud connectivity by design" labels;
  the `NOT-FOR-PRODUCTION.md` in every bundle; the bridge network with no host mounts (the container must not reach the
  host's identity endpoint).
- **The engine changes only upstream** (ADR-0006): rules, model, classifier and normalizer live in the wheel; do not
  re-create `src/network_assessment/{model,rules,classify}` or a lab normalizer (`tests/end_to_end/test_repository_manifest.py`
  fails if they come back). Rule ids are never reused; a changed rule bumps its `version`; `RULES_VERSION` and the
  registry digest pinned in `tests/unit/test_engine.py` move together; live-only rules stay registered so `unknowns[]`
  is stable; a new engine release's topology model marker is added to `MODEL_VERSIONS` in `tests/conftest.py`.
- Every rule title, description, remediation and every finding fact is hedge-free: the wheel's observed-state enforcer
  gates findings at evaluation, and this edition gates rule texts and its own list of hedge words in CI
  (`engine.assert_text_is_hedge_free`, `tests/unit/test_engine.py`, `scripts/rules-doc.py`). Every `learn_url` and
  every framework reference stays `[VERIFY]` until the owner confirms it. `docs/rules/catalog.md` is generated
  (`make rules-doc`).
- No secrets, tokens, customer inventories or real tenant/subscription ids anywhere, fixtures and tests included.
  Samples use subscriptions `00000000-0000-0000-0000-000000000001` and `…0002` and `hcw-sample-*` names only.
- No vendor names in anything a visitor can read (not the host, edge, verification provider or workspace platform):
  say "human verification" and "expires after two hours".
- Owner-pasteable commands: no placeholders; bash and PowerShell both acceptable.
- `/api/health` is flat (`id`, `version` at the top level); the pane posts `{type:'hcw-addon', id, state}` with states
  `loading | ready | working | unavailable` to each origin in `siteOrigins` only; the concurrency-cap error is
  `503 overloaded` with `Retry-After: 2`.
- ADRs: this edition's own in `docs/adr/` (next number: 0007); upstream ones copied with a header. Record limitations in
  `VALIDATION.md`. Keep `CHANGELOG.md` current. Pull requests open ready for review and follow the template.
