# ADR-0005: Always-on guided workspace handoff with one-time bundle tokens

- **Status:** Accepted
- **Date:** 2026-10-11
- **Applies to:** `saulpatinojr/HCW-NetworkEyes_AddOn` (lab edition) and handoff notes for `saulpatinojr/HCW-NetworkEyes_App` (appliance team)

## Context

The sibling Migration AddOn (`saulpatinojr/HCW-AzMigrateOrchestrator_Addon`, ADR-0023) introduced a guided workspace handoff (`POST /api/assessments/{id}/workspace`) that issues a single-use bundle token and launches a disposable Linux container workspace (`docker.io/hybridcloudworks/hcw-lab:latest`) preloaded with the assessment bundle (`bundle.zip`) in `code-server`. In the Migration AddOn, that workspace provider was initially optional (`disabled` by default).

For Network Assessment (`network-assessment`), the owner decided to adopt the same guided workspace handoff pattern and make it **always on** (never optional or disabled) so every visitor who runs an assessment can open the generated bundle (`report.md`, `findings.json`, `topology.json`, `summary.json`, `rules.json`, `NOT-FOR-PRODUCTION.md`) directly inside a disposable Linux container workspace on the lab host.

## Decision

1. **Always-on workspace capability (`workspace: "coder"`):**
   - `CAPABILITIES` in `src/network_assessment/edition.py` always includes `"workspace"`.
   - `GET /api/health` and `GET /api/config` always report `"workspace": "coder"`. There is no `"disabled"` workspace provider mode.
2. **Single-use, short-lived bundle token (`x-bundle-token`):**
   - `AssessmentStore.issue_bundle_token(assessment_id, owner_token, ttl_seconds=600)` verifies the caller's `x-owner-token` and mints a single-use token stored by SHA-256 hash (`_bundle_tokens`), expiring in `min(assessment.expires_at, now + 600)`.
   - `AssessmentStore.redeem_bundle_token(assessment_id, bundle_token)` atomically pops the token hash on first lookup and returns `(assessment, files)` only when the assessment ID matches and neither the token nor the assessment has expired.
   - `GET /api/assessments/{id}/bundle.zip` accepts either `x-owner-token` (browser download) or `x-bundle-token` (workspace startup script). The `x-owner-token` never leaves the browser.
3. **Dual-mode `CoderWorkspaceProvider` (`src/network_assessment/workspace.py`):**
   - When `CODER_SESSION_TOKEN` is configured, `POST /api/assessments/{id}/workspace` calls `POST {CODER_URL}/api/v2/users/me/workspaces` with template `CODER_TEMPLATE_ID` (`na-guided-lab`) and rich parameters `assessment_id`, `bundle_token`, and `api_base_url` (`NA_PUBLIC_BASE_URL`), returning `202` with `status: "pending"`.
   - When `CODER_SESSION_TOKEN` is unset (the default on the lab host when visitors authenticate with their own GitHub session on `coder.lab.hybridcloudworks.com`), `POST /api/assessments/{id}/workspace` returns `202` with `status: "ready"` and a pre-parameterised auto-create deep link (`{CODER_URL}/templates/{CODER_TEMPLATE_ID}/workspace?mode=auto&...`).
4. **Disposable Linux container template (`infrastructure/coder/template/main.tf`):**
   - Uses the digest-pinned `docker.io/hybridcloudworks/hcw-lab` Linux container image under the ADR-0032 / LAB-5 boundary (`tcp://coder-docker-proxy:2375`, `user = "65534:65534"`, `HOME = "/tmp/home"`, per-workspace named volume and isolated bridge network `coder-ws-<id>`, `privileged = false`, `no-new-privileges:true`, all Linux capabilities dropped, `module "code-server"` with `subdomain = true`, and `/usr/local/libexec/hcw-boot/hcw-boot network-assessment` / `python3 -m zipfile -e` bundle extraction). Windows VMs are never used.
5. **Visitor-facing copy rule preserved:**
   - The pane button and status note say `"Open in lab workspace"`, `"Lab workspace ready (...)"`, and `"Open lab workspace"`, never naming the workspace vendor in visible text (`tests/e2e/lab.spec.ts`).

## Appliance Team Handoff (`saulpatinojr/HCW-NetworkEyes_App`)

- **Core engine untouched:** No files under `src/network_assessment/{model,rules,classify}` (`PROVENANCE.md`) were modified.
- **API & UI surface additions in the lab edition:**
  - Added `src/network_assessment/workspace.py` (`CoderWorkspaceProvider`, `WorkspaceInfo`, `WORKSPACE_PROVIDER = "coder"`).
  - Added `POST /api/assessments/{assessment_id}/workspace` (`202 Accepted`) and `x-bundle-token` support on `GET /api/assessments/{assessment_id}/bundle.zip` in `src/network_assessment/routes/assessments.py`.
  - Added `issue_bundle_token` and `redeem_bundle_token` in `src/network_assessment/store.py`.
  - Added `NA_PUBLIC_BASE_URL`, `CODER_URL`, `CODER_SESSION_TOKEN`, `CODER_TEMPLATE_ID`, and `NA_WORKSPACE_TTL_MINUTES` in `src/network_assessment/config.py`.
  - Added `"workspace": "coder"` to `/api/health` and `/api/config`, and `"workspace"` to `CAPABILITIES`.
  - Added `#open-workspace` (`Open in lab workspace`) to `web/index.html` and `web/app.js`.
