# Website integration guide

How `hybridcloudworks.com` shows the Network Assessment lab edition, per the HCW AddOn Integration Standard (website
repository `docs/standards/addon-integration-standard.md`, ADR 0035). The site frames this AddOn in a sandboxed pane on
one page; nothing from this repository is installed into the site bundle.

## Identity

| Item | Value |
|---|---|
| AddOn id | `network-assessment` |
| Site route | `/tools/network-assessment` (`frontend/src/pages/tools/AddOnPanePage.jsx` with `addonId="network-assessment"`; `NetworkAssessmentPage.jsx` wrapper) |
| Origin | `https://network-assessment.lab.hybridcloudworks.com` (exactly `'https://' + id + '.lab.hybridcloudworks.com'`) |
| Frame `src` | `https://network-assessment.lab.hybridcloudworks.com/` exactly (the site builds `origin + panePath` and adds no query string). The pane still honours `?theme=dark` or `?theme=light` if a caller passes one; the site does not, so without it the pane follows `prefers-color-scheme` (read 2026-10-24: `addonPaneUrl` in the catalogue, and `AddOnPanePage.jsx` has no theme handling) |
| Health path | `/api/health` |
| Function App setting (status proxy) | `ADDON_NETWORK_ASSESSMENT_URL` = the origin, plain app setting (public value) |
| Lab-host vault key | `vault_addon_network_assessment_turnstile_secret` |
| Lab-host loopback port | 18082 |
| Image | `docker.io/hybridcloudworks/hcw-addon-network-assessment`, pinned by digest in the website's `lab-host/ansible/group_vars/all.yml` `addons[]` |

## Catalogue row (`frontend/src/data/addons/catalogue.js`)

The website's row is the authority. This is a copy of it as of 2026-10-24 (website commit 5757bb71, the last change to that file). An earlier copy, written
before the row shipped, was kept here and drifted: the site's title, summary, pane path, technology, status and
capabilities all ended up different from it. When this block and the website disagree, the website is right.

```js
{
  id: 'network-assessment',
  title: 'Cloud network assessment',
  summary: 'Upload an export of your Azure network resources and get an assessment of its topology, segmentation and exposure, with the findings explained. Nothing you upload is kept beyond two hours.',
  origin: 'https://network-assessment.lab.hybridcloudworks.com',
  panePath: '/',
  healthPath: '/api/health',
  providers: ['azure'],
  technology: ['azure-networking', 'resource-graph'],
  status: 'available',
  capabilities: ['navigate', 'downloads'],
  docsUrl: 'https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn#readme',
  articleSlugs: []
}
```

The row became `available` on 2026-10-12 (website #1089), when the digest was pinned. `title`, `summary` and
`comingReason` obey the site's public-copy rule (no vendor names; "human verification", "expires after two hours").

## Status proxy

`GET /api/public/addons/network-assessment/status` (anonymous, registered in `functions/src/lib/addons/registry.js`
with `setting: 'ADDON_NETWORK_ASSESSMENT_URL', healthPath: '/api/health'`) reads this AddOn's `/api/health` with a 5 s
timeout and projects exactly `configured, reachable, version, edition, capabilities, asOf`. Every other health field
(`rules`, `model`, `limits`, `turnstile`, `siteOrigins`, `azureConnectivity`) is for the pane and is never forwarded.
The pane mounts only when the proxy answers `configured: true, reachable: true`; otherwise the page shows
"This tool isn't available right now."

## Pane protocol

The pane posts, to each origin in its own `/api/health.siteOrigins` (env `NA_SITE_ORIGINS`, never `*`):

```json
{ "type": "hcw-addon", "id": "network-assessment", "state": "ready" }
```

| State | When |
|---|---|
| `loading` | As soon as the health read answers (the pane needs `siteOrigins` before it can post anything) |
| `ready` | Health answered `ok: true` with `id: network-assessment`; after every upload completes or fails |
| `working` | While `POST /api/assessments` is in flight |
| `unavailable` | Health failed or answered another id (also shown in-pane with the one sentence) |

If the API is down before the first health read, the pane cannot know the site origins and posts nothing; the page's
30 s watchdog shows the unavailable sentence. The site accepts a message only when `event.origin === origin`,
`event.source === frame.contentWindow`, `data.type === 'hcw-addon'`, `data.id === 'network-assessment'` and
`data.state` is one of the four. This AddOn sends no `navigate` and requires no message from the site.

## Sandbox and capabilities

Base sandbox `allow-scripts allow-same-origin allow-forms`. This row asks for:

- `downloads` -> `allow-downloads`: the bundle zip and the sample files are saved from inside the pane.
  **[REVIEW REQUIRED]** Owner decision as a website security change (standard section 21, ADR 0035). The pane works
  without it: "Copy report" puts `report.md` on the clipboard and the report is rendered in a selectable block, and the
  pane says so when a download does not start.
- `clipboard` -> `allow="clipboard-write"` on the frame for "Copy report" (a `document.execCommand('copy')` fallback
  inside the user gesture exists for browsers that refuse the API).

Never `allow-top-navigation`; `allow-popups` is not requested.

**What the site grants today (read 2026-10-24):** `navigate`, `downloads`. That differs from what this AddOn asked for above: `clipboard` (`clipboard-write`) is not granted, and `navigate` is granted although this AddOn never sends one. Whether that is intended is the owner's to confirm against ADR 0035; until then "Copy report" depends on its in-gesture fallback.

## Content security policy, both sides

- Site: `frame-src` gains `https://network-assessment.lab.hybridcloudworks.com` (derived from `addonOrigins()`).
- AddOn: `frame-ancestors` from `NA_FRAME_ANCESTORS`, set by the role to the two site origins, equal to the host's
  `caddy_frame_ancestors` (both policies are enforced by the browser; they must agree). `X-Frame-Options: DENY` is sent
  only when the value is `'none'` (the default, which is what a direct visit outside the lab host sees).

## Environment table (rendered by the website's `addons` role)

| Variable | Store | Value on the lab host |
|---|---|---|
| `PORT` | `addons[].env` | `8080` |
| `NA_FRAME_ANCESTORS` | `addons[].env` | `https://hybridcloudworks.com https://www.hybridcloudworks.com` |
| `NA_SITE_ORIGINS` | `addons[].env` | `https://hybridcloudworks.com https://www.hybridcloudworks.com` |
| `NA_ALLOWED_ORIGINS` | `addons[].env` | empty (the pane is same-origin with its API) |
| `NA_PUBLIC_HOST` | `addons[].env` | `network-assessment.lab.hybridcloudworks.com` (the verification token's hostname must equal it) |
| `NA_PUBLIC_BASE_URL` | `addons[].env` | `https://network-assessment.lab.hybridcloudworks.com` |
| `CODER_URL` | `addons[].env` | `https://coder.lab.hybridcloudworks.com` (always-on guided workspace handoff, ADR-0005) |
| `CODER_TEMPLATE_ID` | `addons[].env` | `na-guided-lab` |
| `CODER_SESSION_TOKEN` | optional vault | optional; when absent, workspace handoff uses browser-session deep links |
| `NA_WORKSPACE_TTL_MINUTES` | `addons[].env` | `240` |
| `NA_TRUST_PROXY` | `addons[].env` | `1` (the host's reverse proxy sets `X-Forwarded-For`) |
| `NA_TURNSTILE_SITE_KEY` | `addons[].env` | the widget's public site key |
| `TURNSTILE_SECRET` | vault | `vault_addon_network_assessment_turnstile_secret` (`secret_env`) |
| `NA_ALLOW_NO_TURNSTILE` | never set on the host | absent (fail closed) |
| `NA_TTL_MINUTES`, `NA_MAX_ITEMS`, `NA_RATE_LIMIT_POSTS`, `NA_RATE_LIMIT_WINDOW_MINUTES`, `NA_MAX_CONCURRENT` | `addons[].env` | defaults `120`, `200`, `10`, `10`, `2` |
| `NA_TELEMETRY` | image default | `0` (this edition emits nothing) |

## Copy rules for anything a visitor reads

No vendor or tool names on either side of the frame: not the host, the edge, the human-verification provider, the
workspace platform. Say "human verification" and "expires after two hours". The in-pane unavailable sentence is
exactly `This tool isn't available right now.` Status is shown in words (`Checking…`, `Ready`, `Assessing…`,
`Unavailable`), never by colour alone. `tests/e2e/lab.spec.ts` scans the pane's text for the forbidden words.

## Acceptance tests on the website side

Catalogue row validity and registry parity, `AddOnPanePage.test.jsx` (status gate, exact sandbox for
`['downloads', 'clipboard']`, `allow`, watchdog, message acceptance), `csp.test.js` parity, route completeness, public
copy with `data/addons` in its roots, the status proxy with a fake fetch answering this AddOn's health shape.
