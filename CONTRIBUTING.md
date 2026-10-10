# Contributing

1. Fork/branch, `uv sync`, make the change, then `uv run ruff check . && uv run ruff format --check .`, `uv run python scripts/rules-doc.py --check`, `uv run pytest -q --cov=src`, and `make e2e` for pane or API changes.
2. Engine changes (`src/network_assessment/{model,rules,classify}`) are changes to ported code (ADR-0001): record them in `PROVENANCE.md` and in the file's header line; never reuse a rule id; bump the rule's `version`; move `RULES_VERSION` and the pinned registry digest together; keep every text hedge-free.
3. New or changed rules carry a `learn_url` on `learn.microsoft.com` (marked `[VERIFY]` until the owner confirms it), framework mappings in `rules/frameworks.py`, a test, and, if the sample's results change, a re-pin in `tests/unit/test_sample_expectations.py`; regenerate `docs/rules/catalog.md` (`make rules-doc`).
4. Fill the PR template honestly: what you ran, what you did not, and why. Pull requests open ready for review.
5. Keep `VALIDATION.md` and `CHANGELOG.md` current; edition-relevant upstream ADRs are copied into `docs/adr/`.
6. Be kind; see `CODE_OF_CONDUCT.md`.
