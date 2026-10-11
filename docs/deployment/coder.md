# Guided workspace handoff (Coder browser lab)

Every Network Assessment run in the lab edition can be opened in an isolated Linux container workspace (`na-guided-lab` on the shared lab host). Workspace handoff is **always on** (ADR-0005).

## Architecture

1. **In-pane action (`Open in lab workspace`):**
   - Calls `POST /api/assessments/{id}/workspace` with the assessment's `x-owner-token`.
2. **One-time bundle token:**
   - The lab API issues a single-use, 10-minute token (`bundle_token`) scoped exclusively to `GET /api/assessments/{id}/bundle.zip` via the `x-bundle-token` header.
   - The owner token never leaves the visitor's browser.
3. **Workspace launch (`CoderWorkspaceProvider`):**
   - **Direct API provisioning (when `CODER_SESSION_TOKEN` is set):** `POST {CODER_URL}/api/v2/users/me/workspaces` creates workspace `na-<first-8-of-id>` from template `CODER_TEMPLATE_ID` (`na-guided-lab`) with rich parameters `assessment_id`, `bundle_token`, and `api_base_url` (`NA_PUBLIC_BASE_URL`), returning `status: "pending"` and `launchUrl: "{CODER_URL}/@me/na-<id8>"`.
   - **Browser-session deep-link provisioning (default when `CODER_SESSION_TOKEN` is unset):** Returns `status: "ready"` and `launchUrl: "{CODER_URL}/templates/{CODER_TEMPLATE_ID}/workspace?mode=auto&name=na-<id8>&param.assessment_id=...&param.bundle_token=...&param.api_base_url=..."` so the signed-in visitor's browser session creates the workspace automatically.
4. **Container startup (`infrastructure/coder/template/main.tf`):**
   - Runs the digest-pinned `docker.io/hybridcloudworks/hcw-lab` Linux container image under the ADR-0032 / LAB-5 boundary (`tcp://coder-docker-proxy:2375`, `user = "65534:65534"`, `HOME = "/tmp/home"`, `privileged = false`, `no-new-privileges:true`, `capabilities { drop = ["ALL"] }`, isolated per-workspace bridge network `coder-ws-<id>`, 1 CPU / 2 GiB hard limits, no Docker socket, no host path, no cloud credentials).
   - Dispatches to `/usr/local/libexec/hcw-boot/hcw-boot network-assessment` (with inline `python3 -m zipfile -e` fallback), fetching `/api/assessments/{assessment_id}/bundle.zip` once via `x-bundle-token` into `/tmp/home/assessment` and serving `code-server` on its own subdomain (`subdomain = true`, compatible with `CODER_DISABLE_PATH_APPS=true`).

## Template deployment

Publish on the lab host via `/usr/local/sbin/hcw-coder-template-push na-guided-lab`, or from a machine with the `coder` CLI authenticated to `https://coder.lab.hybridcloudworks.com` (or via `.github/workflows/coder-template.yml` when `CODER_TEMPLATE_ENABLED=true`):

```bash
coder templates push na-guided-lab --directory infrastructure/coder/template --yes
```
