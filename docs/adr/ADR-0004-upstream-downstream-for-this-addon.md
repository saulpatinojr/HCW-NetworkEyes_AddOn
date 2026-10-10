# ADR-0004: Upstream/downstream for this AddOn: the Core publishes, this edition consumes and never forks


> **Amended 2026-10-10.** The owner merged the Core lineage back into `saulpatinojr/HCW-NetworkEyes_App` the same day, so
> that repository is the App and the upstream of this edition; `Work-Cloud_Network_Core` is no longer written to. Read
> "the Core" below as the App. The engine wheel is a GitHub Release asset of each `engine-v*` tag there, pinned here by
> URL and sha256 (`core-update.yml`), so no PyPI step stands between a release and its adoption.

Status: accepted, 2026-10-10. Scope: `HCW-NetworkEyes_AddOn` (downstream) and `saulpatinojr/HCW-NetworkEyes_App`
(upstream). Applies the program's ADR-0028 model (recorded in `HCW-AzMigrateOrchestrator_App`, copied into the
sibling Python AddOn) to this pair.

## Context

ADR-0028 settled the product model for every pair: the App (here the Core) is the freestanding upstream product that
owns the engine, rules and appliance edition and publishes packages; the AddOn is a strict, slim, downstream web-front
edition that depends on published, versioned artifacts and nothing else upstream, and adopts releases "if compatible".
For this pair the published artifact does not exist yet (ADR-0001), the Core is a different GitHub repository than the
archived `HCW-NetworkEyes_App` this program could write to, and the Core's refactor is specified in that archived
repository's `REFACTOR_APP.md` addressed to Core paths.

## Decision

| Repository | Holds | Publishes |
|---|---|---|
| `saulpatinojr/HCW-NetworkEyes_App` (**upstream**) | The engine (`packages/cna-azure-network-engine`: model, rules with a registry and `RULES_VERSION`, classifier, findings, Markdown/JSON report, Resource Graph normalizer; `[azure]` extra for discovery), the monorepo `cna` package, the appliance edition on Container Apps. Canonical ADR log. | `cna-azure-network-engine` (wheel, tag `engine-v*`), appliance image `docker.io/hybridcloudworks/cna` |
| `saulpatinojr/HCW-NetworkEyes_AddOn` (**downstream**) | Ingestion of uploaded exports, the in-memory store, the FastAPI lab API (`NA_*`), the pane, samples, docs, the lab image. Interim: the ported engine (ADR-0001). | Lab image `docker.io/hybridcloudworks/hcw-addon-network-assessment` |

1. **Direction.** Engine, rule, model and classifier work happens upstream. This edition changes ported code only through
   `PROVENANCE.md` entries while the port exists, and never once the wheel is pinned; a rule it wants is proposed
   upstream.
2. **Downstream flow.** A Core `engine-v*` release is the trigger. `.github/workflows/core-update.yml` (every six hours
   and on demand) compares the latest engine release with the pinned `ENGINE_REF`; when it differs it bumps the pin,
   re-locks, runs this edition's lint, unit, contract, security, catalog-drift and browser e2e suites, and opens a
   ready-for-review pull request labelled `compatible` or `needs-adaptation`. A compatible PR auto-merges only when the
   repository variable `CORE_AUTOMERGE` is `true`. Once the wheel is on PyPI, Dependabot's `pip` ecosystem proposes the
   same bumps and the interim workflow becomes redundant.
3. **Shared contracts the Core must keep.** Rule ids, severities and `applies_to` (hash-pinned in
   `tests/unit/test_registry.py`), `TOPOLOGY_MODEL_VERSION` (the lab's `lab-1.0.0` is declared equivalent to the Core's
   1.3.0 Azure subset), the flat `/api/health` envelope and the `hcw-addon` pane protocol, so one pane bundle serves
   both editions. The Core's `REFACTOR_APP.md` section 21 records the same table from its side.
4. **Boundary (ADR-0008 by analogy).** The Core's `[azure]` extra and discovery modules never enter this edition: the
   lock has no `azure-*`, `msal` or `boto3`; `edition.py` refuses them at import; `publish-images.yml` proves
   `import azure` fails inside the built image.

## Consequences

- This edition is freestanding in deployment (its own image, API, pane) and depends on published, versioned artifacts
  only, once they exist; until then it depends on nothing upstream at all.
- The Core's `REFACTOR_APP.md` is the contract for what it publishes; a change there that renumbers a rule or moves a
  symbol is a `needs-adaptation` PR here, never a silent fork.
- The archived `HCW-NetworkEyes_App` holds only the refactor plan; the implementation target is the Core.
