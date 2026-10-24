# Deployment: the lab host

This AddOn is **hosted by the website repository's `addons` Ansible role** (`HCW-HybridCloudWorks/lab-host/ansible`),
as one `docker_container` named `hcw-addon-network-assessment` behind the host's Caddy, under
`network-assessment.lab.hybridcloudworks.com`. This repository ships no Terraform for the host and must not
(AddOn Integration Standard, section 3). What the role needs from here is below; everything else is the role's.

## The `addons[]` entry (website `lab-host/ansible/group_vars/all.yml`)

| Field | Value |
|---|---|
| `id` | `network-assessment` |
| `image` | `docker.io/hybridcloudworks/hcw-networkeyes` |
| `image_tag` | the release tag, for humans (for example `0.1.0`) |
| `image_digest` | the `sha256:…` printed by `publish-images.yml` in its run summary; the only coupling |
| `port` | `18082` (published as `127.0.0.1:18082:8080`; the role asserts loopback and uniqueness) |
| `memory` | `512m` |
| `pids_limit` | `256` |
| `cpus` | `1` |
| `env` | the public values in the table below |
| `secret_env` | `TURNSTILE_SECRET: vault_addon_network_assessment_turnstile_secret` (the role refuses to start the container when the vault key is unset) |
| `enabled` | `true` to run, `false` to remove the container (kill switch) |

Container flags the role applies: `read_only: true`, `tmpfs: ['/tmp']`, `cap_drop: ['ALL']`,
`security_opts: ['no-new-privileges:true']`, `restart_policy: unless-stopped`, the image's own `HEALTHCHECK`
(`/api/health` through urllib), `log_options` with a max size, no volumes, no socket, the default bridge only (egress
only to the verification endpoint; the host's Arc identity endpoint and `/var/opt/azcmagent` are never reachable or
mounted), under the daemon's user-namespace remap. The image runs as uid 10001 and writes nothing, so a read-only root
filesystem needs no exceptions beyond `/tmp`. The role waits for `http://127.0.0.1:18082/api/health` to answer 200.

## Environment

| Variable | Value on the host | Notes |
|---|---|---|
| `PORT` | `8080` | inside the container |
| `NA_FRAME_ANCESTORS` | `https://hybridcloudworks.com https://www.hybridcloudworks.com` | must equal the host's `caddy_frame_ancestors`; the browser enforces both |
| `NA_SITE_ORIGINS` | `https://hybridcloudworks.com https://www.hybridcloudworks.com` | the role derives it from `caddy_frame_ancestors` minus `'self'` |
| `NA_ALLOWED_ORIGINS` | empty | the pane is same-origin with its API |
| `NA_PUBLIC_HOST` | `network-assessment.lab.hybridcloudworks.com` | the verification token must be bound to this hostname |
| `NA_PUBLIC_BASE_URL` | `https://network-assessment.lab.hybridcloudworks.com` | base URL passed into guided workspace containers to fetch `bundle.zip` |
| `CODER_URL` | `https://coder.lab.hybridcloudworks.com` | always-on guided workspace handoff endpoint (ADR-0005) |
| `CODER_TEMPLATE_ID` | `na-guided-lab` | Coder template (`infrastructure/coder/template/main.tf`) |
| `CODER_SESSION_TOKEN` | optional (vault) | when unset, `POST /api/assessments/{id}/workspace` returns a browser-session deep link |
| `NA_WORKSPACE_TTL_MINUTES` | `240` | guided workspace lifetime (4 hours) |
| `NA_TRUST_PROXY` | `1` | the first `X-Forwarded-For` value is the client address for rate limiting (Caddy sets it; nothing else can reach the port) |
| `NA_TURNSTILE_SITE_KEY` | the widget's site key | public; published by `/api/health` |
| `TURNSTILE_SECRET` | from the vault | never in `group_vars`, Git or the site |
| `NA_TTL_MINUTES` / `NA_MAX_ITEMS` / `NA_RATE_LIMIT_POSTS` / `NA_RATE_LIMIT_WINDOW_MINUTES` / `NA_MAX_CONCURRENT` | `120` / `200` / `10` / `10` / `2` | defaults; set only to change them |
| `NA_ALLOW_NO_TURNSTILE` | **never set** | uploads fail closed without the secret |

## Caddy

The role renders `20-addons.caddy` with `@addon_network_assessment host network-assessment.lab.hybridcloudworks.com`,
`handle @addon_network_assessment { reverse_proxy 127.0.0.1:18082 }` and a `handle_errors` that answers 503 with
`This tool isn't available right now.` `lab_panes_only` already applies site-only `frame-ancestors` and the top-level
redirect to every lab name; this AddOn never sets `lab_top_level_allowed`. No DNS or certificate change: the `*.lab`
record and the wildcard certificate cover one-label names.

## Owner steps (once per AddOn)

1. **Create the human-verification widget** for `network-assessment.lab.hybridcloudworks.com` (managed challenge,
   hostname exactly that name) in the verification provider's dashboard, in the same account the site's widget lives
   in: `https://dash.cloudflare.com/?to=/:account/turnstile`. Copy the site key and the secret.
   `[REVIEW REQUIRED]` one widget per AddOn (standard section 21).
2. **Seed the secret in the lab-host vault** (bash on the host checkout of the website repository, the way its
   `docs/labs-host.md` describes; this line is bash):

   ```bash
   hcw-vault-set vault_addon_network_assessment_turnstile_secret
   ```

   The command prompts for the value; never paste it into a chat or a commit.
3. **Put the site key and the row in `group_vars/all.yml`** (`addons[]` above; `NA_TURNSTILE_SITE_KEY` and
   `NA_PUBLIC_HOST` in `env`).
4. **Docker Hub publishing** (website runbook `docs/runbooks/docker-hub-publishing.md` has the shape): in Docker Home
   create an OIDC connection for this repository trusting `repo:saulpatinojr@34853639/HCW-NetworkEyes_AddOn@<repo-id>:ref:refs/tags/*`
   (the repository id is printed by the command below), then set the repository variables. PowerShell:

   ```powershell
   gh api repos/saulpatinojr/HCW-NetworkEyes_AddOn -q .id
   gh variable set DOCKERHUB_ENABLED --repo saulpatinojr/HCW-NetworkEyes_AddOn --body true
   gh variable set DOCKERHUB_CONNECTION --repo saulpatinojr/HCW-NetworkEyes_AddOn
   ```

   The last command prompts for the connection UUID. Until both variables exist, `publish-images.yml` builds and scans
   but does not push, and the website row stays `coming`.
5. **Tag a release** (`git tag v0.1.0 && git push origin v0.1.0`), read the digest from the run summary, pin it in
   `group_vars/all.yml`, and run the website's `bootstrap.sh`; the role pulls by digest and recreates the container.
   A successful result: `curl -s http://127.0.0.1:18082/api/health` on the host prints `"ok":true` with
   `"id":"network-assessment"`, and `https://hybridcloudworks.com/tools/network-assessment` shows the pane.
   PowerShell from anywhere: `Invoke-RestMethod https://network-assessment.lab.hybridcloudworks.com/api/health` prints
   `edition : lab`.

## Update and rollback

Update: new tag -> new digest -> one website PR moving `image_tag` and `image_digest` -> `bootstrap.sh`. Rollback: the
previous digest in the same file and another run. A restart purges every in-memory assessment by design; the pane says
so before an upload.
