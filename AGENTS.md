# AGENTS.md — guidance for coding agents (Copilot coding agent, Codex, Claude)

This is `saulpatinojr/HCW-NetworkEyes_AddOn`: the lab edition of the Network Assessment (upload-only, in-memory, no
cloud connectivity by design) carrying an interim port of the Core's engine (`PROVENANCE.md`, ADR-0001) that is
replaced by the `cna-azure-network-engine` wheel from `saulpatinojr/HCW-NetworkEyes_App` (the App; a GitHub Release asset of each `engine-v*` tag) once it is adopted: `engine-v0.1.0` has been published since 2026-10-12, adoption is pending. Read `docs/whats-new-upstream.md` first.

Build/test: `uv sync`, then `uv run ruff check . && uv run ruff format --check .`,
`uv run python scripts/rules-doc.py --check`, `uv run pytest -q --cov=src`; browser suite `make e2e`.
Where changes belong: rules, model and classifier changes go upstream to the Core once the wheel exists; until then they
are made here with a `PROVENANCE.md` entry. Conventions and invariants: `CLAUDE.md`. Review expectations:
`.github/copilot-instructions.md`. AI-created changes go through the review -> fix -> current-head verification cycle
before merge.
