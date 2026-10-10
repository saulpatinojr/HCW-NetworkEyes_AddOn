# Deployment: the Azure appliance (upstream, not here)

The appliance edition is the App's: `saulpatinojr/HCW-NetworkEyes_App` (the former Core, merged back on 2026-10-10), specified by the `REFACTOR_APP.md`
written into the archived `HCW-NetworkEyes_App` (change set G and sections 12 and 15). It runs as **one Consumption
Azure Container App** per client scope with a user-assigned managed identity holding `Reader` on the allowlisted
scopes (plus the optional reader roles and the custom `CNA Network BGP Reader` role for the live-only rules), refreshes
its Resource Graph snapshot on a timer (one query set per refresh, never per visitor), serves cached results, has no
upload route, and is published from the Core as `docker.io/hybridcloudworks/cna`. Nothing in this repository deploys to
Azure.

Container Apps answer (validated in the program's design, not assumed): the appliance needs an Azure identity, scheduled
outbound Resource Graph and ARM calls and a public HTTPS endpoint, and nothing else; Container Apps provides identity,
TLS, scaling and logs with no VM or cluster, and the sibling App's Terraform is the template. Recommendation carried
from the program decisions (CONTRACT-DECISIONS item 21): `min_replicas 1`, `max_replicas 1`; scale-to-zero loses the
in-memory snapshot on idle and is an owner option (with a persisted last-good snapshot), not the default. The lab
edition stays on the lab host (ADR-0003): it needs no identity, and on the host "no identity reachable" is a
configuration fact.

Why the **lab** image refuses managed-identity endpoints: `src/network_assessment/edition.py` checks, at import of
the application, that no cloud SDK is importable and that none of `IDENTITY_ENDPOINT`, `MSI_ENDPOINT`,
`AZURE_CLIENT_SECRET`, `AZURE_FEDERATED_TOKEN_FILE`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` is set, and exits non-zero
otherwise. A lab image started inside an Azure compute environment that offers an identity therefore never serves a
request: the edition boundary (AddOn Integration Standard, section 19; ADR-0008 by analogy, ADR-0004) is enforced at
runtime, not only by the absence of packages. `publish-images.yml` proves both: `import azure` fails inside the image,
and a container started with `IDENTITY_ENDPOINT` set exits.
