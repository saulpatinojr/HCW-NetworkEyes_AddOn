# Operations runbook (lab edition)

The container is run by the website repository's `addons` role on the lab host (`docs/deployment/lab-host.md`). The
commands below are bash on the host unless stated. Nothing here touches a cloud.

| Task | How | What success looks like |
|---|---|---|
| Health | `curl -s http://127.0.0.1:18082/api/health` | `{"ok":true,"id":"network-assessment","version":"0.1.0","edition":"lab",…,"azureConnectivity":"disabled-by-design","rules":{"version":"2026.10.0","count":45,"liveOnly":11},"model":{"version":"lab-1.0.0"},…}` within a second |
| Which version is live | `curl -sI http://127.0.0.1:18082/api/health \| grep -i x-addon-version` | `x-addon-version: 0.1.0` |
| Logs | `docker logs --since 1h hcw-addon-network-assessment` | JSON lines on stderr: `startup` (rule count), `assessment_created` (rows, resources, findings, unknowns, warnings, duration), `assessment_read`, `assessment_rejected` (a code), `assessment_deleted`, `rate_limited`, `overloaded`, `turnstile_rejected` (a count of codes), `sweep`, `shutdown`. Never ids, names, tokens, file names, prefixes or cell content. |
| Restart | `docker restart hcw-addon-network-assessment` | Health answers again within the `HEALTHCHECK` start period (10 s). Every in-memory assessment is gone by design. |
| Upgrade / rollback | Move `image_tag` and `image_digest` in the website's `group_vars/all.yml`; run `bootstrap.sh` | The role pulls by digest, recreates the container and waits for health. Rollback is the previous digest. |
| Stop serving (kill switch) | Website: unset `ADDON_NETWORK_ASSESSMENT_URL` (the proxy answers `configured:false`, the page shows the one sentence). Host: `enabled: false` on the row and run `bootstrap.sh` (the container is removed; Caddy answers 503 with the same sentence). | Visitors see `This tool isn't available right now.` and nothing else |
| Abuse | Per client address: `NA_RATE_LIMIT_POSTS` per `NA_RATE_LIMIT_WINDOW_MINUTES` (defaults 10 / 10) and `NA_MAX_CONCURRENT` (2). Tighten in `addons[].env`; human verification is already required on every upload. A burst shows as `rate_limited` and `overloaded` log lines. | 429 / 503 answers with `Retry-After`; health stays 200 |
| Verification outage | Uploads answer `403 turnstile_failed` with code `verification-unavailable` (the siteverify call failed within 5 s). Nothing to do on the host; the pane tells the visitor to retry. | Health unaffected |
| Rotate the verification secret | `hcw-vault-set vault_addon_network_assessment_turnstile_secret` on the host checkout, then `bootstrap.sh` (the role recreates the container with the new value) | Health 200; an upload with a fresh token answers 201 |
| Data request | There is nothing to retrieve or erase: assessments live in process memory for at most `NA_TTL_MINUTES` (120), are returned only to the holder of the owner token, and a restart purges everything. State this in the reply. | — |
| Memory or pids pressure | The role caps the container at 512m and 256 pids; the store holds at most `NA_MAX_ITEMS` (200) assessments (oldest evicted) of at most 5 MB input each. | `docker stats hcw-addon-network-assessment` stays under the caps |

Troubleshooting a container that will not start: `docker logs hcw-addon-network-assessment` prints one line
`{"event":"startup_refused","reason":"…"}` (exit code 3) when the edition guard refused (an identity endpoint or a
credential variable in the environment) or a setting is out of range (`NA_*` numeric settings are integers between
their minimum and 1,000,000,000). Neither is fixed on the host beyond removing the offending environment.
