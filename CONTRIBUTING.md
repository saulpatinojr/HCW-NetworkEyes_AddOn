# Contributing

1. Fork/branch, `uv sync`, make the change, then `uv run ruff check . && uv run ruff format --check .`, `uv run python scripts/rules-doc.py --check`, `uv run pytest -q --cov=src`, and `make e2e` for pane or API changes.
2. Engine changes (rules, model, classifier, normalizer) are made upstream in `saulpatinojr/HCW-NetworkEyes_App` and arrive here as a released wheel through `core-update.yml`'s bump pull request (ADR-0006); there is no engine code in this repository to change.
3. When a bump changes rules: move `RULES_VERSION` and the registry digest pinned in `tests/unit/test_engine.py` together, add the release's topology model marker to `MODEL_VERSIONS` in `tests/conftest.py`, re-pin `tests/unit/test_sample_expectations.py` if the sample's results change, and regenerate `docs/rules/catalog.md` (`make rules-doc`). Every rule's `learn_url` stays `[VERIFY]` until the owner confirms it.
4. Fill the PR template honestly: what you ran, what you did not, and why. Pull requests open ready for review.
5. Keep `VALIDATION.md` and `CHANGELOG.md` current; edition-relevant upstream ADRs are copied into `docs/adr/`.
6. Be kind; see `CODE_OF_CONDUCT.md`.
