# What's new upstream

This lab edition is built from the engine in `saulpatinojr/HCW-NetworkEyes_App` (the "App"). This file is the
running list of what changed there and what, if anything, this repository has to do about it.

## How to use this file

Read it before you change behaviour here, and read the **Current upstream state** table first: it says in plain words
which version of the App's engine this repository really runs. When you adopt an upstream change, or decide one does
not matter, add or edit an entry in the same pull request so the next person (or the next Claude session) does not
have to rediscover it.

## Current upstream state

Checked on 2026-10-24 against the App's `main` branch, its releases and its tags. On 2026-10-31 the tags were checked again
(`git ls-remote`: `engine-v0.1.0` is still the only engine tag) and the `engine-v0.1.0` wheel was compared with the port
(entry below); the App's `main` was not re-read that day, so the first row still says 2026-10-24.

| Question | Answer |
|---|---|
| App `main` | Commit `592512b`, after pull request [#264](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/264). Update this row when you adopt something. |
| Latest engine release | **`engine-v0.1.0`**, published 2026-10-12 by `320-release-engine.yml` ([run](https://github.com/saulpatinojr/HCW-NetworkEyes_App/actions/runs/38205653284), success). [Release page](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.0). |
| Its files | `cna_azure_network_engine-0.1.0-py3-none-any.whl`, sha256 `a609b80059fca7b22057b464a0c41895b324e21dc3e28d569a6e0894e94bd1ba` (re-computed by downloading it on 2026-10-24), and `cna_azure_network_engine-0.1.0.tar.gz`, sha256 `1672ff3d656143f83bf0759d27ed26806b4e8884017af3a3ff7c99387af84b1e` (as reported by GitHub). URL pattern: `https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/download/engine-v0.1.0/cna_azure_network_engine-0.1.0-py3-none-any.whl`. |
| Engine package name | The App renamed the engine package on 2026-10-27, in a pull request that is not released yet: distribution `network-assessment-azure-engine`, import name `network_assessment_azure_engine`. `engine-v0.1.0` stays published under the old name, so the next release under the new name needs a version above 0.1.0 (the tag `engine-v0.1.0` exists). |
| Other App tags | `v0.1.0` and `v0.8.0` (application releases from the App's earlier history, not the engine). There is no `v0.10.0` and no second engine release. |
| Engine package changes since `engine-v0.1.0` | Four commits, all Dependabot version bumps inside `packages/cna-azure-network-engine/pyproject.toml` (eight changed lines). No source file changed. The package version is still `0.1.0`, so a new release needs a version bump first. |
| What this repository runs | The **interim port** of the engine at App commit `5d3b914` (`PROVENANCE.md`, ADR-0001), under `src/network_assessment/{model,rules,classify}`. Lab code reaches it only through `src/network_assessment/engine.py`, which runs the wheel instead as soon as the wheel is installed. The wheel is **not adopted** yet. |
| `core-update.yml` | **Armed.** `pyproject.toml` has the marker line `# ENGINE_REF none`, so the next scheduled run (every six hours, at minute 41) sees `none` against `0.1.0`, pins the `engine-v0.1.0` wheel, re-locks, runs the compatibility check and opens the bump pull request with the HCW Main Admin App. |
| Version markers | `RULES_VERSION` is `2026.10.0` in both. `TOPOLOGY_MODEL_VERSION` is `lab-1.0.0` in the port (declared equivalent to the App's 1.3.0 Azure subset) and `1.4.0` in the wheel; the wheel's model is a superset of the port's. `FINDINGS_MODEL_VERSION` is `lab-1.0.0` in the port, `FINDINGS_SCHEMA_VERSION` `1.1.0` in the wheel. |
| Is `engine-v0.1.0` compatible? | **No, not yet.** Tested on 2026-10-31 (entry below): ids, versions, severities, `applies_to`, the live-only set, the classifier and the normalizer agree; five things in the engine do not, and they are fixed upstream, not here. |

In short: the wheel this repository was waiting for exists, the lab can now run on it unchanged, and the bump pull
request will open by itself. It will say **needs adaptation** for `engine-v0.1.0`, because of five differences in the
engine that only a new App release can fix.

## Entries, newest first

### 2026-10-31: adopting `engine-v0.1.0`, compared with the port

- **What was done.** The wheel was installed from the `engine-v0.1.0` tag and, separately, downloaded from the release
  (its sha256 is `a609b80059fca7b22057b464a0c41895b324e21dc3e28d569a6e0894e94bd1ba`, the value already recorded above).
  Both engines were run over the three samples, and the bump that `core-update.yml` makes was rehearsed in a scratch
  copy: the pin line, `uv lock`, the whole test suite, the browser suite and the lab image (`VALIDATION.md`, run of
  2026-10-31).
- **What agrees.** The rule ids, versions, severities and `applies_to` (the registry digest pinned in
  `tests/unit/test_registry.py` is the same, `7424a4a3…71339`); `RULES_VERSION` `2026.10.0`; the 45 rules with the same
  11 live-only ones, and the wheel still registers them, so an export reports all 11 in `unknowns[]` (the wheel lists a
  live-only rule as unknown whenever its live inputs are absent, which an export never has); the topology classifier;
  the Resource Graph normalizer (the wheel's is ported from this repository's `ingestion/normalize.py` and gives the same
  topology, facts and warnings on every sample). The wheel's model is a superset of the port's: it adds fields and
  classes for live data and renames `AzureTopology.model_version` to `schema_version`.
- **What does not agree (upstream fixes, in the order they matter).**
  1. **AZ-NET-007 version 2 and AZ-NET-025 ignore a linked WAF policy.** The port's version 2 reads the policy an
     Application Gateway links to; the wheel's reads only the inline WAF setting. On the sample, the WAF_v2 gateway
     `hcw-sample-agw-public`, protected by the policy `hcw-sample-wafpolicy` in Detection mode, gets a false HIGH
     "WAF is disabled" (AZ-NET-007) and loses its MEDIUM "Detection mode" (AZ-NET-025). Same rule versions, different
     behaviour, which the "a changed rule bumps its version" rule exists to prevent.
  2. **Rule texts are missing.** 43 of the 45 rules have no rule-level description or remediation (the wheel writes
     them on each finding instead), so the catalog and `GET /api/rules` would show empty texts; the findings of
     AZ-NET-001 to 007, 011, 012, 014 and 018 carry none at all.
  3. **Hedge words.** The remediation of AZ-COST-002 and of AZ-NET-031's findings says "expected", which the
     observed-state enforcer refuses here (this edition gates remediation as well as titles and descriptions).
  4. **Evidence references** start with `discovery:azure_<subscription>` instead of `export:<subscription>`, which
     `docs/api/openapi.yaml` and the user guide promise.
  5. Smaller: AZ-NET-031 keys its finding on the private-link connection (`…/privateLinkServiceConnections/<name>`)
     rather than the private endpoint, so the finding id changes; AZ-NET-004's fact reads `NoneMbps` when the export
     has no bandwidth; live-only `unknowns[]` reasons are field paths (`network_metrics.gateway_metrics[]…`) rather than
     the sentence the pane shows today.
- **Reaches this repository?** Yes. This repository's side is done in this change: `src/network_assessment/engine.py`
  is the one place lab code imports the engine from, and it runs the wheel when installed; the normalizer hand-off,
  the rule list, the model marker (`topology.json` keeps its `model_version` key) and the tests were adapted;
  `tests/unit/test_engine.py` states what this edition needs from any engine; `core-update.yml` can now make the first
  pin (it reads the wheel's file name from the release, so `engine-v0.1.0` is pinned under its own name), regenerates
  `docs/rules/catalog.md` in the bump and commits it; `pyproject.toml` allows the URL pin (`allow-direct-references`),
  without which the bump could not build at all.
- **Trust.** Merging an engine bump means running the App's code, and that code runs inside this edition's own tests,
  so it can make them pass. `core-update.yml` keeps the App key out of the job that runs it (two jobs, see the
  workflow's header), but auto-merge still trusts the release. Since the follow-up to pull request 67, auto-merge no
  longer reads the bump job's report at all: with `CORE_AUTOMERGE` set to `true` it is turned on for every bump pull
  request, `needs-adaptation` ones included, and only the pull request's own required checks stop the merge.
  `CORE_AUTOMERGE` was `true` on 2026-10-31. The recommendation is to set it to `false` until the two-job workflow has opened one real bump pull request; the
  variable is the owner's to change, on the repository's
  [Actions variables page](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/settings/variables/actions).
- **Action.** Ask the App for a release that fixes items 1 to 4 (item 5 is worth fixing in the same release). Until
  then the bump pull request for `engine-v0.1.0` stays open and labelled `needs-adaptation`; do not merge it, and do not
  patch the engine here. When the fixed release is tagged, `core-update.yml` opens a new bump pull request for it (a new
  branch, `core-update/engine-v<version>`); close the `engine-v0.1.0` one then. After the first green bump is merged,
  delete the port in its own pull request (the deletion plan in `PROVENANCE.md`).


### 2026-10-27: the engine package is renamed (not released yet)

- **What changed.** In the App, the engine package `cna-azure-network-engine` becomes `network-assessment-azure-engine` (import name `network_assessment_azure_engine`, directory `packages/network-assessment-azure-engine`) as step 4 of the owner's rename of the App's short code name to "network assessment". The release workflow `320-release-engine.yml` builds the wheel and the sdist under the new names. The first release, `engine-v0.1.0`, was published under the old name and stays there.
- **Reaches this repository?** Yes, in one place: `core-update.yml` looks for the engine wheel by name. It is inert today (there is no `ENGINE_REF` line), and this pull request moves its package name, its wheel file-name pattern and its commit message to the new names so that it still works on the first release under the new name. No code here imports the engine, so nothing else changes. This repository has its own package with the same import name as the App's application package (`network_assessment`, renamed there in step 1); the two are never installed together.
- **Action.** ~~Pin the first release under the new name; edit an old-name pin by hand.~~ Superseded on 2026-10-31: `core-update.yml` now reads the wheel's file name from each release and rewrites the whole `ENGINE_REF` line, so `engine-v0.1.0` is pinned under its old name and a later release under the new one, with no hand edit. `src/network_assessment/engine.py` imports either name.

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
- **Action: adopt it, as its own pull request (App `REFACTOR_APP.md` change set C).** Done as far as this repository can go on 2026-10-31 (entry above): the steps below now happen through `core-update.yml`, and the comparison found five things to fix upstream first.
  1. Add the pin line to `pyproject.toml` in the form `core-update.yml` reads (the release tag, the wheel file name and a `# ENGINE_REF 0.1.0` marker on one line; the workflow's header comment shows the exact shape). Now: the marker `# ENGINE_REF none` is in `pyproject.toml` and the workflow writes the pin line.
  2. Run `uv lock`, then `uv run pytest -q --cov=src`, `uv run python scripts/rules-doc.py --check` and `make e2e`.
  3. Compare the results with the port: `RULES_VERSION`, the rule ids in `docs/rules/catalog.md`, and `tests/unit/test_sample_expectations.py`. A difference is a "needs adaptation" item, not a reason to edit the wheel here.
  4. Only when those agree, delete `src/network_assessment/{model,rules,classify}`, remove their `PROVENANCE.md` rows, and update `CLAUDE.md`, `AGENTS.md`, `README.md` and this file.
  5. Record what ran and what did not in `VALIDATION.md`.

## Open upstream decisions that will affect this repository

| Decision | Where it is tracked | Why it matters here |
|---|---|---|
| Protect `engine-v*` tags | App `TODO.md` T-730 | Until done, a moved tag could change what your pinned URL serves. The sha256 pin still protects you. |
| Turn on PyPI publishing for the engine | App `TODO.md` T-728, first bullet | Not needed for this repository (it pins the GitHub Release), but it changes how others install the engine. |
| A release that fixes the five differences of 2026-10-31 (entry above) | **Not tracked in the App yet**: no issue was opened there from this repository | Until it exists, every bump here says `needs-adaptation` and nothing merges: auto-merge may be turned on, but it waits for the required checks, which fail. |
| Next engine release (a new version) | App `REFACTOR_APP.md` section 15, steps 3 and later | Change set B brings `RULES_VERSION` bumps and web findings ids; each arrives here as a `core-update.yml` pull request. |
| Docker Hub sign-in for the App's own image builds | App `REVIEW.md` R-013 | Concerns the App's images, not this repository's image. |
