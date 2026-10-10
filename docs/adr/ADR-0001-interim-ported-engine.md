# ADR-0001: The lab edition ports the Core's engine with provenance, as an interim measure until the wheel exists


> **Amended 2026-10-10.** The owner merged the Core lineage back into `saulpatinojr/HCW-NetworkEyes_App` the same day, so
> that repository is the App and the upstream of this edition; `Work-Cloud_Network_Core` is no longer written to. Read
> "the Core" below as the App. The engine wheel is a GitHub Release asset of each `engine-v*` tag there, pinned here by
> URL and sha256 (`core-update.yml`), so no PyPI step stands between a release and its adoption.

Status: accepted, 2026-10-10. Scope: `HCW-NetworkEyes_AddOn`; depends on `saulpatinojr/HCW-NetworkEyes_App`
(`REFACTOR_APP.md` change sets A, B, C, E and J, written into the archived `HCW-NetworkEyes_App`).

## Context

The Core at `5d3b914` holds the Azure network model, two rule engines (Engine A in `cna/ai_engine/analysis_engine.py`
with stable rule ids and framework mappings; Engine B in `apps/cna-api/main.py` with untyped dicts and no ids), the
BC/DR and FinOps generators, the topology classifier and the observed-state enforcer, all inside a monorepo that also
depends on the Azure SDKs, Postgres, Foundry and draw.io. The program needs a lab edition on the website now, framed at
`/tools/network-assessment`, that evaluates an estate without ever holding a credential. The Core's installable engine
wheel (`cna-azure-network-engine`, pydantic only in its base) does not exist yet. Owner decision 2026-10-09: port with
provenance under MIT, `[REVIEW REQUIRED]` for relicensing (the Core labels itself Proprietary).

## Decision

1. **The lab edition is upload-only.** Its input is a Resource Graph export of `microsoft.network/*` rows (JSON array or
   `az graph query` envelope; Resource Graph Explorer CSV; the portal "All resources" CSV accepted with a warning). It
   has no sign-in, no cloud SDK, no live reads, no persistence, no execution. It refuses to start where a managed
   identity is offered (`edition.py`) and reports `azureConnectivity: disabled-by-design`.
2. **The engine is ported, bounded and reviewed, not vendored.** About 1,100 lines across six Core modules land under
   `src/network_assessment/{model,rules,classify}` with a `# Ported from … at 5d3b914; changes: …` header per file and
   a root `PROVENANCE.md` (file, source path, lines, what changed, why). The two engines become one typed registry
   (`rules/registry.py`: `@rule`, `RULES_VERSION`, `evaluate()` with the Core's `rule_id:resource_id` dedup); Engine
   B's checks become AZ-NET-020..033 and AZ-BCDR-006/007 with the severities in the design; rules that need live reads
   are registered `live-only` and surface in `unknowns[]`. The normalizer (`ingestion/normalize.py`) is new code and
   the reference for the Core's `normalize/resource_graph.py`.
3. **The port is interim.** When the Core publishes `cna-azure-network-engine`, `core-update.yml` pins the exact
   version (`ENGINE_REF`), the ported directories are deleted, their `PROVENANCE.md` rows are removed, and the lab keeps
   only its own code (ingestion, store, API, security, pane). Until then ported code changes only through
   `PROVENANCE.md` entries, rule ids are never reused, a changed rule bumps its `version`, and `RULES_VERSION` moves
   with the pinned registry digest in `tests/unit/test_registry.py`. The Core must not renumber.
4. **Honesty is in the data.** Every finding carries `observedState { state, fact, evidenceRef }` with a hedge-free fact
   (the enforcer gates facts at evaluation and rule texts in CI); rules the export cannot answer are `unknowns[]` with
   a reason; `NOT-FOR-PRODUCTION.md` ships in every bundle; the "What this cannot tell you" panel and `report.md` say
   what no export carries.
5. **Framework mappings are data.** `rules/frameworks.py` keeps the Core's compliance references keyed by rule id;
   every one is `[VERIFY]` in the catalog and `[REVIEW REQUIRED]` for legal/compliance review; every `learn_url` is
   `[VERIFY]` until the owner confirms it.

## Consequences

- The lab can ship before the Core's refactor lands; the Core's change sets produce the same symbols, so the port is
  removable without semantic change.
- Duplication of about 1,100 lines for the interim, with a recorded deletion plan and a workflow that watches for the
  wheel.
- The relicensing of ported code under MIT is an owner decision recorded in `NOTICE` and awaiting confirmation.
- `tests/security/test_edition_boundary.py` and the image-level check in `publish-images.yml` make the boundary
  enforceable rather than documented.
