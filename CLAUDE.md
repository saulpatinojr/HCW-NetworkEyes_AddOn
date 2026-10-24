# CLAUDE.md — working agreement for Claude Code in this repository

This is `saulpatinojr/HCW-NetworkEyes_AddOn`, the **lab edition** of the Network Assessment (AddOn id
`network-assessment`, site route `/tools/network-assessment`, origin `https://network-assessment.lab.hybridcloudworks.com`):
a Python 3.14 FastAPI application that evaluates an uploaded Azure Resource Graph export of `microsoft.network/*` rows
against typed network rules, a vanilla pane the website frames, fictional samples, docs, a hardened Dockerfile and
SHA-pinned workflows. The engine under `src/network_assessment/{model,rules,classify}` is an **interim port** of the
App's engine (`saulpatinojr/HCW-NetworkEyes_App` at `5d3b914`, ADR-0001, `PROVENANCE.md`); it is deleted, not handed
upstream, once the wheel is adopted. The App published `cna-azure-network-engine` 0.1.0 as the `engine-v0.1.0` GitHub
Release on 2026-10-12; it is **not adopted yet** (no `ENGINE_REF` line, so `core-update.yml` is inert). The wheel is a
GitHub Release asset of every `engine-v*` tag, pinned here by URL and sha256 through `core-update.yml`.
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
- **The ported engine is interim and changes only through `PROVENANCE.md` entries** until the wheel exists: a change to
  any file with a `# Ported from …` header is recorded in its header line and in the table, with the reason. Rule ids
  are never reused; a changed rule bumps its `version`; `RULES_VERSION` and the registry digest pinned in
  `tests/unit/test_registry.py` move together; live-only rules stay registered so `unknowns[]` is stable.
- Every rule title, description, remediation and every finding fact is hedge-free (`model/enforcer.py` gates them at
  evaluation and in CI); every `learn_url` and every framework reference stays `[VERIFY]` until the owner confirms it.
  `docs/rules/catalog.md` is generated (`make rules-doc`).
- No secrets, tokens, customer inventories or real tenant/subscription ids anywhere, fixtures and tests included.
  Samples use subscriptions `00000000-0000-0000-0000-000000000001` and `…0002` and `hcw-sample-*` names only.
- No vendor names in anything a visitor can read (not the host, edge, verification provider or workspace platform):
  say "human verification" and "expires after two hours".
- Owner-pasteable commands: no placeholders; bash and PowerShell both acceptable.
- `/api/health` is flat (`id`, `version` at the top level); the pane posts `{type:'hcw-addon', id, state}` with states
  `loading | ready | working | unavailable` to each origin in `siteOrigins` only; the concurrency-cap error is
  `503 overloaded` with `Retry-After: 2`.
- ADRs: this edition's own in `docs/adr/` (next number: 0006); upstream ones copied with a header. Record limitations in
  `VALIDATION.md`. Keep `CHANGELOG.md` current. Pull requests open ready for review and follow the template.
