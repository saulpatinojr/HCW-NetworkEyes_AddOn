# Routes to add to the website

| Route | Page | Notes |
|---|---|---|
| `/tools/network-assessment` | `frontend/src/pages/tools/NetworkAssessmentPage.jsx` -> `<AddOnPanePage addonId="network-assessment" />` | One `lazyPage` wrapper in `App.jsx` (routes stay hand-declared, not a `:id` parameter); `staticRoutes.networkAssessment` in `routeFactory.ts` |

- Pre-render: `scripts/prerender-entry.jsx` derives `ADDON_ROUTES` from the catalogue, so this route pre-renders once
  the row exists; while the row is `coming` the built page is the explainer (title, summary, `comingReason`, a link back).
- Route inventory: one entry for `/tools/network-assessment`; `routes-are-complete.test.js` expects it declared and
  pre-rendered.
- Tools menu: the Header derives its items from `availableAddons`, so the item appears when the row flips to `available`.
- No provider-scoped variant (`/azure/tools/network-assessment` is not created); `providers: ['azure']` is hub-card metadata.
- The AddOn's own routes are in `../api/openapi.yaml`; the site calls only `GET /api/health`, server side, through the
  status proxy.
