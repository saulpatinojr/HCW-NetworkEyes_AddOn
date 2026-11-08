# AGENTS.md — guidance for coding agents (Copilot coding agent, Codex, Claude)

This is `saulpatinojr/HCW-NetworkEyes_AddOn`: the lab edition of the Network Assessment (upload-only, in-memory, no
cloud connectivity by design) that runs the `network-assessment-azure-engine` wheel from `saulpatinojr/HCW-NetworkEyes_App`
(the App; a GitHub Release asset of each `engine-v*` tag), pinned on the `# ENGINE_REF` line of `pyproject.toml`. The
interim port of the engine that used to live here was deleted on 2026-11-08 (ADR-0006). Read `docs/whats-new-upstream.md` first.

Build/test: `uv sync`, then `uv run ruff check . && uv run ruff format --check .`,
`uv run python scripts/rules-doc.py --check`, `uv run pytest -q --cov=src`; browser suite `make e2e`.
Where changes belong: rules, model, classifier and normalizer changes go upstream to the App, are released as an
`engine-v*` wheel and arrive through `core-update.yml`; they are never made here. Conventions and invariants: `CLAUDE.md`. Review expectations:
`.github/copilot-instructions.md`. AI-created changes go through the review -> fix -> current-head verification cycle
before merge.
