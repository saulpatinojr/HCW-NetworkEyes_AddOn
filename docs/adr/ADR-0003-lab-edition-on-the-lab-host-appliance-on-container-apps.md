# ADR-0003: The lab edition runs on the lab host; the appliance on Azure Container Apps

Status: accepted, 2026-10-10. Scope: this repository (lab); `saulpatinojr/Work-Cloud_Network_Core` (appliance, by its
`REFACTOR_APP.md` change set G and section 12).

## Context

The website already operates a lab host (`*.lab.hybridcloudworks.com` behind Caddy, configured by the website
repository's Ansible) with a pane model, a status proxy and a hardening baseline, and ADR 0032 there reserves Compose
for Coder. The program decided that every AddOn is one hardened container on that host, published by digest to Docker
Hub, framed by the site. The appliance edition, by contrast, must run inside the client's Azure tenant under a managed
identity with Reader on allowlisted scopes, refresh its Resource Graph snapshot on a timer and serve cached results; the
lab host can neither offer that identity nor should.

## Decision

- **Lab edition: the lab host.** One `docker_container` named `hcw-addon-network-assessment`, image
  `docker.io/hybridcloudworks/hcw-addon-network-assessment` by digest, loopback port 18082, hostname
  `network-assessment.lab.hybridcloudworks.com`, env from `group_vars`, secret from the host vault
  (`vault_addon_network_assessment_turnstile_secret`), run by the website repository's generic `addons` role with
  read-only root, `tmpfs /tmp`, `cap_drop ALL`, `no-new-privileges`, 512m, 256 pids, one CPU, the image's own
  `HEALTHCHECK`, no volumes, no socket, the default bridge network only (no `network_mode: host`, no
  `/var/opt/azcmagent` mount, so the host's Arc identity endpoint is unreachable from inside), user-namespace remap
  composing with the image's uid 10001. This repository ships no Terraform for the host and only a local
  `docker-compose.yml` for development. The lab needs no Azure identity, credential or outbound Azure call; on the host
  "no identity reachable" is a configuration fact, whereas on Container Apps it would be a platform identity the lab
  must prove it does not use.
- **Appliance edition: Azure Container Apps**, specified upstream: one Consumption Container App per client scope with
  a user-assigned managed identity holding `Reader` (plus the optional reader roles and the custom BGP reader role the
  Core's `REFACTOR_APP.md` change set F names), image by digest, timer-driven Resource Graph refresh with cached
  results (no per-visitor queries, no upload route), `min_replicas 1`, `max_replicas 1` recommended (scale-to-zero
  loses the in-memory snapshot and is an owner option, not the default; CONTRACT-DECISIONS item 21), Terraform in the
  Core's appliance repository. The lab image refuses to start there (`edition.py`), and the appliance image is a
  different build target of the Core's one Dockerfile that is never framed by the site.
- **Publishing** for both is tag-driven, scanned before push (Trivy HIGH/CRITICAL, fixed only), with provenance, SBOM
  and attestation, through the Docker OIDC connection rather than long-lived registry credentials.

## Consequences

- The site's coupling to this AddOn is one digest in `group_vars` plus one app setting; rollback is the previous digest.
- The lab host's resource ceiling gains one container (512m / 256 pids); the website records it next to the Coder
  capacity assertion.
- Running the lab anywhere that offers an identity endpoint is impossible by construction, which keeps the two editions
  from being confused in deployment as well as in code.
