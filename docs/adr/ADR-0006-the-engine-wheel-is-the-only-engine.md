# ADR-0006: The engine wheel is the only engine; the interim port is deleted

Status: accepted, 2026-11-08. Supersedes decision 3 of ADR-0001 ("The port is interim") and the parts of decisions 2,
4 and 5 that name the ported files. Scope: `HCW-NetworkEyes_AddOn`; depends on `saulpatinojr/HCW-NetworkEyes_App`.

## Context

ADR-0001 put a copy of the App's engine (the "interim port") under `src/network_assessment/{model,rules,classify}`,
with a `# Ported from …` header on each file and a row per file in a root `PROVENANCE.md`, so the lab could ship
before the App published its engine as an installable package (a "wheel", the file format Python packages are
installed from). It also recorded the plan for removing that copy once the wheel was adopted.

The App now publishes the engine as `network-assessment-azure-engine` on each `engine-v*` GitHub Release. This edition
adopted it at `0.1.1` (pull request 78) and moved to `0.1.2` (pull request 87); `pyproject.toml` pins it by URL on the
`# ENGINE_REF 0.1.2` line and `uv.lock` records its sha256. Since then `src/network_assessment/engine.py` ran the
wheel, and the port was only exercised by its own tests (`tests/unit/test_registry.py`, the ported rule, enforcer and
classifier tests) and by the comparison of the two normalizers. Keeping it meant two engines with different rule
versions (`2026.10.0` in the port, `2026.11.0` in the wheel) in one tree, and a quiet fallback to the old one whenever
the wheel was missing.

## Decision

1. **The wheel is the only engine.** `src/network_assessment/{model,rules,classify}`, the lab's own normalizer
   (`ingestion/normalize.py`, which built the port's model), the tests that only tested the port and `PROVENANCE.md`
   are deleted. The table and the list of what was not ported stay readable in git history (the last commit that had
   them is the parent of this change).
2. **No fallback.** `engine.py` imports the wheel or raises `EngineNotInstalled` (an `ImportError`) with a message that
   names the package and says to run `uv sync`; the application imports it at startup, so a missing wheel stops the
   lab before it serves anything. `GET /api/health` and `GET /api/rules` always report the wheel's distribution name
   and version in `engine`; the `interim-port` value is gone.
3. **The lab keeps its own gates.** The wheel validates every finding with its observed-state enforcer at evaluation
   (title, description and the observed fact). This edition still owns the list of hedge words it refuses
   (`EDITION_HEDGE_WORDS` in `tests/unit/test_engine.py`) and the check that every rule text is present and hedge-free
   (`engine.assert_text_is_hedge_free`, used by that test and by `scripts/rules-doc.py`), so an engine release that
   loosens either fails this edition's CI. The registry digest, `RULES_VERSION`, the live-only list and the topology
   model marker stay pinned in `tests/unit/test_engine.py` and `tests/conftest.py`.
4. **Engine changes go upstream only.** A rule, model, classifier or normalizer change is made in the App, released as
   an `engine-v*` wheel, and arrives through `core-update.yml`'s bump pull request. Nothing here patches the engine.
   `tests/end_to_end/test_repository_manifest.py` fails if the port's folders, `PROVENANCE.md` or an import of them
   comes back.

## Consequences

- One engine, one rule version, one place to change it. About 4,800 lines (the port, its tests, the lab normalizer and `PROVENANCE.md`) leave the tree.
- The comparison that proved the wheel's normalizer matches the lab's own is gone with the lab's normalizer; the
  normalizer behaviour is still pinned by `tests/unit/test_normalize.py`, which runs against the wheel.
- The framework mappings now live only in the wheel. They stay `[VERIFY] [REVIEW REQUIRED]` in `docs/rules/catalog.md`
  and in `NOTICE`, as before.
- ADR-0001's decisions 1 (upload only, no cloud connectivity) and 4 (honesty in the data) still stand; only the parts
  about the ported copy are superseded.
