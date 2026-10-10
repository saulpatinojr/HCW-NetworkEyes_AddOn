> Copied from HCW-CloudAssessor_AddOn/docs/adr/ADR-0002-shared-addon-skeleton-no-kit-yet.md on 2026-10-10 (the sibling Python AddOn, where the decision was recorded first); it applies to both repositories as written and is not edited here.

# ADR-0002: One shared AddOn skeleton convention across the Python AddOns; no `hcw-addon-kit` package yet

Status: accepted, 2026-10-10. Scope: this repository and `HCW-NetworkEyes_AddOn`.

## Context

Two program AddOns are Python (this one and the network assessment); the third (migration) is TypeScript. All three
implement the same HTTP and container contract (HCW AddOn Integration Standard): the flat `/api/health` envelope, the
error envelope, security headers with configurable `frame-ancestors`, exact-origin CORS, human verification with the
fail-closed posture, body/row/item caps, a per-client token bucket with `X-Forwarded-For` behind `<PREFIX>_TRUST_PROXY`,
a concurrency bound, content-free logs, an in-memory TTL store with hashed owner tokens, the `hcw-addon` pane bridge,
the two-stage hash-pinned Dockerfile on the website's base digest, and the same workflow set.

## Decision

- The two Python AddOns share **one skeleton convention**, module for module: `config.py` (`<PREFIX>_*`), `edition.py`
  (import-time guard), `store.py`, `security/{turnstile,headers,cors,limits,ratelimit,logging}.py`, `routes/*`,
  `app.py` (`create_app(settings)`), `__main__.py`; `web/{index.html,app.js,styles.css,theme.css}`; the same `tests/`
  layout; the same docs tree; the same `infrastructure/docker/{Dockerfile,versions.env}`; the same four workflows.
- **No shared package yet.** A `hcw-addon-kit` (the skeleton as a library: settings, store, verification, headers,
  limits, logging, the pane bridge) is the obvious third step, but extracting it before the second Python AddOn has
  run against real traffic would freeze guesses. The standardization pass at the end of Phase 5 compares the two trees
  and records the divergences the kit would have to absorb.
- Divergence is allowed only where the domain differs (ingestion, catalog or rules, scoring, reports); anything in the
  contract layer that differs between the two is a bug in one of them.

## Consequences

- Reviewers can read one AddOn and review the other; the website integrates both the same way.
- Some duplication (a few hundred lines) until the kit exists; the cost of a premature abstraction was judged higher.
- When the kit is extracted, both AddOns adopt it in the same release train and this ADR is superseded.
