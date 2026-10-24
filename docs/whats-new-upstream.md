# What's new upstream

This lab edition is built from the engine in `saulpatinojr/HCW-NetworkEyes_App` (the "App"). This file is the
running list of what changed there and what, if anything, this repository has to do about it.

## How to use this file

Read it before you change behaviour here, and read the **Current upstream state** table first: it says in plain words
which version of the App's engine this repository really runs. When you adopt an upstream change, or decide one does
not matter, add or edit an entry in the same pull request so the next person (or the next Claude session) does not
have to rediscover it.

## Current upstream state

Checked on 2026-10-24 against the App's `main` branch, its releases and its tags.

| Question | Answer |
|---|---|
| App `main` | Commit `592512b`, after pull request [#264](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/264). Update this row when you adopt something. |
| Latest engine release | **`engine-v0.1.0`**, published 2026-10-12 by `320-release-engine.yml` ([run](https://github.com/saulpatinojr/HCW-NetworkEyes_App/actions/runs/38205653284), success). [Release page](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.0). |
| Its files | `cna_azure_network_engine-0.1.0-py3-none-any.whl`, sha256 `a609b80059fca7b22057b464a0c41895b324e21dc3e28d569a6e0894e94bd1ba` (re-computed by downloading it on 2026-10-24), and `cna_azure_network_engine-0.1.0.tar.gz`, sha256 `1672ff3d656143f83bf0759d27ed26806b4e8884017af3a3ff7c99387af84b1e` (as reported by GitHub). URL pattern: `https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/download/engine-v0.1.0/cna_azure_network_engine-0.1.0-py3-none-any.whl`. |
| Other App tags | `v0.1.0` and `v0.8.0` (application releases from the App's earlier history, not the engine). There is no `v0.10.0` and no second engine release. |
| Engine package changes since `engine-v0.1.0` | Four commits, all Dependabot version bumps inside `packages/cna-azure-network-engine/pyproject.toml` (eight changed lines). No source file changed. The package version is still `0.1.0`, so a new release needs a version bump first. |
| What this repository runs | The **interim port** of the engine at App commit `5d3b914` (`PROVENANCE.md`, ADR-0001), under `src/network_assessment/{model,rules,classify}`. The wheel is **not adopted**. |
| `core-update.yml` | Inert. It looks for an `ENGINE_REF` line in `pyproject.toml`; there is none, so it finds nothing to do and exits cleanly (`VALIDATION.md`). |
| Version markers | `RULES_VERSION` is `2026.10.0` in both the wheel and this port. `TOPOLOGY_MODEL_VERSION` is `lab-1.0.0` here (declared equivalent to the App's 1.3.0 Azure subset) and `1.4.0` in the wheel. `FINDINGS_MODEL_VERSION` is `lab-1.0.0` here. **Whether the wheel's model and rules behave the same as this port has not been tested.** |

In short: the wheel this repository has been waiting for exists. Nobody has yet tried swapping it in.

## Entries, newest first

### 2026-10-24: pull request [#265](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/265) (documents) and this file

- **What changed.** The App's `CHANGELOG.md`, `TODO.md`, `REFACTOR_APP.md`, `README.md` and `CLAUDE.md` were brought up to date, and the App's `CLAUDE.md` now says to add an entry here whenever a change reaches this repository.
- **Reaches this repository?** No code. It is why this file exists.
- **Action.** None. Keep this file current.

### 2026-10-24: branch and tag protection on the App ([#258](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/258) to [#261](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/261))

- **What changed.** The App's `main` branch now needs a pull request and green key checks, and cannot be deleted or force-pushed. Tags matching `v*` can no longer be moved or deleted.
- **Reaches this repository?** Yes, indirectly: you pin the engine by release URL and sha256, so a moved or deleted tag would break the pin. **`engine-v*` tags are not covered** (the rule matches `refs/tags/v*`; App `TODO.md` T-730 tracks closing the gap).
- **Action.** When you adopt the wheel, keep the URL **and** the sha256 pinned (your design already does). Until T-730 is done, treat the sha256 as the authority, not the tag.

### 2026-10-24: Python dependency updates in the App ([#231](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/231) to [#238](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/238))

- **What changed.** The App cleared 55 `pip-audit` advisories: pillow 13.0.0, virtualenv 21.14.13, setuptools 84.1.0, opentelemetry-api 1.45.1, certifi 2026.10.19, brotlicffi 1.2.1.0, brotli 1.2.1 and filelock 4.2.1.
- **Reaches this repository?** Partly. This repository's `uv.lock` has certifi 2026.10.19 and opentelemetry-api 1.45.1 (already current) but **`filelock` 4.1.1**. On 2026-10-24 `pip-audit` reported six known vulnerabilities in it, all fixed in 4.2.1. It is a development-only dependency (pulled in by `pip-audit`'s cache), not part of the image.
- **Action.** Bump `filelock` in `uv.lock` (see this repository's `CHANGELOG.md` for the pull request), then re-run `uvx pip-audit`.

### 2026-10-24: web application dependencies in the App ([#263](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/263), [#264](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/264))

- **What changed.** `zod` 4.6.7 and an override forcing `@azure/msal-node` 7.1.1 in the App's Next.js web app, plus several version bumps from Dependabot #224. A real Azure sign-in through the App's web app has not been tested yet (App ticket [#241](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/241)).
- **Reaches this repository?** No. This repository has no Node application and no `@azure/identity`; its pane is plain HTML, CSS and JavaScript and it cannot sign in to Azure by design.
- **Action.** Nothing.

### 2026-10-24: continuous-integration pins in the App ([#262](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/262))

- **What changed.** The secret scanner image is pinned by digest, `ruff` is pinned to 0.17.1, `pre-commit` to 4.7.0, and `$GITHUB_OUTPUT` is quoted in the release workflow.
- **Reaches this repository?** No. This repository has its own workflows and pins.
- **Action.** Nothing. If you want the same pins here, do it as its own change.

### 2026-10-12: first engine release, `engine-v0.1.0`

- **What changed.** `cna-azure-network-engine` 0.1.0 was published as a GitHub Release (Azure network topology model, typed rule registry, classifier, Resource Graph normalizer and report renderers). The App's `320-release-engine.yml` builds, tests and uploads it on every `engine-v*` tag; publishing to PyPI stays off until the App's `PYPI_PUBLISH_ENABLED` variable is `true` (App `TODO.md` T-728), which does not matter here because you pin the GitHub Release.
- **Reaches this repository?** Yes. This is the release `PROVENANCE.md`, ADR-0001 and `core-update.yml` were written to wait for.
- **Action: adopt it, as its own pull request (App `REFACTOR_APP.md` change set C).**
  1. Add the pin line to `pyproject.toml` in the form `core-update.yml` reads (the release tag, the wheel file name and a `# ENGINE_REF 0.1.0` marker on one line; the workflow's header comment shows the exact shape).
  2. Run `uv lock`, then `uv run pytest -q --cov=src`, `uv run python scripts/rules-doc.py --check` and `make e2e`.
  3. Compare the results with the port: `RULES_VERSION`, the rule ids in `docs/rules/catalog.md`, and `tests/unit/test_sample_expectations.py`. A difference is a "needs adaptation" item, not a reason to edit the wheel here.
  4. Only when those agree, delete `src/network_assessment/{model,rules,classify}`, remove their `PROVENANCE.md` rows, and update `CLAUDE.md`, `AGENTS.md`, `README.md` and this file.
  5. Record what ran and what did not in `VALIDATION.md`.

## Open upstream decisions that will affect this repository

| Decision | Where it is tracked | Why it matters here |
|---|---|---|
| Protect `engine-v*` tags | App `TODO.md` T-730 | Until done, a moved tag could change what your pinned URL serves. The sha256 pin still protects you. |
| Turn on PyPI publishing for the engine | App `TODO.md` T-728, first bullet | Not needed for this repository (it pins the GitHub Release), but it changes how others install the engine. |
| Next engine release (a new version) | App `REFACTOR_APP.md` section 15, steps 3 and later | Change set B brings `RULES_VERSION` bumps and web findings ids; each arrives here as a `core-update.yml` pull request. |
| Docker Hub sign-in for the App's own image builds | App `REVIEW.md` R-013 | Concerns the App's images, not this repository's image. |
