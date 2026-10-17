## Summary

<!-- What changes and why. Name the AddOn Integration Standard section or the ADR this affects. -->

## Verification

- [ ] `uv run ruff check . && uv run ruff format --check .` — result:
- [ ] `uv run python scripts/rules-doc.py --check` — result:
- [ ] `uv run pytest -q --cov=src` — result (tests, coverage):
- [ ] `npx playwright test -c tests/e2e/playwright.config.ts` — result, or CI run link:
- [ ] Checks not run and why:

## Rules (if `src/network_assessment/rules/**` or `model/**` changed)

- [ ] The change is recorded in `PROVENANCE.md` (ported code changes only through its entries until the Core's wheel exists, ADR-0001)
- [ ] Rule ids are never reused; a changed rule bumps its `version`; `RULES_VERSION` and the pinned digest in `tests/unit/test_registry.py` move together
- [ ] Titles, facts and remediation stay hedge-free (the enforcer gates them); `learnUrl` stays `[VERIFY]` until the owner confirms it
- [ ] `docs/rules/catalog.md` regenerated (`make rules-doc`); `tests/unit/test_sample_expectations.py` re-pinned if the sample's results changed

## Infrastructure (if `infrastructure/**` or `docker-compose.yml` changed)

- [ ] `versions.env` and every `FROM` agree; `uv lock --check` passes
- [ ] No privileged containers, host network, host mounts, Docker socket exposure or secrets introduced

## Security and data review

- [ ] No real tenant, subscription or resource identifiers anywhere (samples use `00000000-0000-0000-0000-000000000001` and `…0002`)
- [ ] Nothing weakens the edition boundary, the fail-closed human verification, owner-token isolation, the limits, exact-origin CORS or the "not production" labels

## AI provenance

- [ ] Code created or changed by an AI coding partner (GitHub Copilot / Claude / Codex); reviewer applies the review -> fix -> current-head verification cycle
