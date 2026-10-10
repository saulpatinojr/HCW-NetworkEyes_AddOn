# GitHub Copilot repository instructions

Treat GitHub Copilot as one teammate with separate review and remediation hats: `copilot-pull-request-reviewer[bot]`
reviews; `copilot-swe-agent` fixes only when explicitly requested. A fix that demonstrably closes the original finding
closes that finding: acknowledge and resolve the thread, then evaluate the current head. Handle disagreement on-thread
with evidence and a counter-proposal. Never treat a stale-head check as current evidence.

## This repository

`saulpatinojr/HCW-NetworkEyes_AddOn` is the **lab edition** of the Network Assessment: a Python 3.14 FastAPI
application (`src/network_assessment`) that evaluates an uploaded Azure Resource Graph export of `microsoft.network/*`
rows against typed network rules ported, with provenance, from `saulpatinojr/Work-Cloud_Network_Core` at `5d3b914`
(`PROVENANCE.md`, ADR-0001), plus a vanilla pane (`web/`), fictional samples, docs, a hardened Dockerfile and
SHA-pinned workflows.

Review against `CLAUDE.md`'s invariants. In particular: the lab must stay technically unable to reach Azure (no cloud
SDK, import-time refusal under identity endpoints, `tests/security/test_edition_boundary.py`); uploads stay gated by
human verification unless `NA_ALLOW_NO_TURNSTILE=1` (local only); owner tokens are hashed and compared in constant
time; 5 MB / 5,000 rows / 200 items / 120 minutes; logs carry no visitor data; no vendor names in visitor copy; ported
engine code changes only through `PROVENANCE.md` entries; every finding fact is hedge-free; every `learnUrl` and
framework reference is `[VERIFY]` until the owner confirms it; samples use only subscriptions
`00000000-0000-0000-0000-000000000001` and `00000000-0000-0000-0000-000000000002`.
