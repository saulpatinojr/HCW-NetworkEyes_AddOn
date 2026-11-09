# Changelog

All notable changes to this repository are recorded here. The format follows Keep a Changelog; versions are semver tags.

## [Unreleased]

### Fixed

- **Prepared for engine 0.1.5** ([HCW-NetworkEyes_App#376](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/376), not released yet). Upstream now checks each rule's remediation and framework notes for hedge words, rewords two notes, and moves `AZ-NET-009` and `AZ-NET-019` to version 2 and `RULES_VERSION` to `2026.11.1`. `docs/whats-new-upstream.md` says what the bump has to re-pin (the registry digest and `RULES_VERSION` in `tests/unit/test_engine.py`, two catalog rows); `tests/conftest.py` knows the `0.1.5` model version ahead of time. Documentation and one test row only.

- **The notes say where the HCW Main Admin App is installed today.** `VALIDATION.md` and the comments in `.github/workflows/core-update.yml` said the App "is being added" to HCW-CloudCrawler_App and HCW-CloudAssessor_App, or would be there "once the owner adds it"; it has been installed there since 2026-11-05. The proof run is tracked on [HCW-CloudCrawler_App#70](https://github.com/saulpatinojr/HCW-CloudCrawler_App/issues/70). Wording only.

- **The image names the licences of its Hybrid Cloud Works code, and carries their texts.** The lab image installs the engine wheel `network-assessment-azure-engine` (Apache-2.0, from `saulpatinojr/HCW-NetworkEyes_App`) beside this repository's own code (MIT), but its label `org.opencontainers.image.licenses` said only `MIT`, and the image held no licence text at all. The MIT License asks for its notice with every copy, and section 4 of the Apache License asks anyone who passes the software on to include the licence and the NOTICE; the released `engine-v0.1.2` wheel ships neither file itself. Now: the label is the SPDX expression (the standard way to write a combination of licences) `MIT AND Apache-2.0`; new `third_party/network-assessment-azure-engine/LICENSE` (a byte-for-byte copy of the App's Apache-2.0 `LICENSE`) and `NOTICE` (the engine package's own, from [HCW-NetworkEyes_App#360](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/360)); the `lab` stage copies `third_party/` to `/usr/share/licenses/` and this repository's `LICENSE` and `NOTICE` to `/usr/share/licenses/hcw-networkeyes-addon/`, root-owned and read-only to uid 10001; `NOTICE` names the engine, its copyright holder (Hybrid Cloud Works) and both paths. The `image` job of `ci.yml` and the boundary step of `publish-images.yml` now expect the new label and check that the licence files are in the built image. New `tests/security/test_image_licences.py` pins the label, the licences it names against `LICENSE`, `pyproject.toml` and the installed wheel's metadata, the bundled files, the `COPY` lines and both workflow checks; `repository.manifest.json` lists the new files.

- **`docs/api/openapi.yaml` parses as YAML again.** The `x-bundle-token` header's description held an unquoted `{id}`, which ends the flow mapping it sits in, so a strict YAML parser rejected the whole file; the route contract test reads lines, not YAML, and did not notice. The description is quoted, and `tests/contract/test_openapi_routes.py` now fails on any unquoted description containing a `{`.

### Changed

- **Runs engine 0.1.5** ([pull request 97](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/97)): `network-assessment-azure-engine 0.1.5` (was `0.1.4`). Upstream now checks each rule's remediation and framework notes for hedge words too, and two notes were reworded to say what was observed, so rules `AZ-NET-009` and `AZ-NET-019` are at version 2 and the rule set is `2026.11.1`. `AZ-NET-009` also has a new title, "Azure Firewall with no rule hits or no processed data", matching what it checks. The pinned registry digest, the rule-set version in the tests and the browser test, and `docs/rules/catalog.md` move with it. What the rules find does not change.

- **Runs engine 0.1.4** ([pull request 93](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/93)): `network-assessment-azure-engine 0.1.4` (was `0.1.3`). An upload whose resource names contain a hedge word such as "may" (for example `app-may-gw`) no longer fails with a server error: a hedge word is now excused only inside a customer identifier (a resource name, id or location with no spaces, joined by `-`, `.`, `/` or `:`; descriptions, tags and other customer text are still checked), and a finding that still fails its hedge check is withheld and listed in `unknowns[]` with a fixed reason instead of stopping the assessment ([HCW-NetworkEyes_App#356](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/356)). `engine.py` re-exports that reason as `HEDGED_WORDING_REASON`. The evaluation gate test now checks that a hedged finding is withheld, never reported; new tests check that the samples have nothing withheld and that renamed resources give the same findings. Rules and model are unchanged; `docs/rules/catalog.md` changes only its generated provenance line (engine `0.1.3` → `0.1.4`).

- **Ready for engine 0.1.4** ([HCW-NetworkEyes_App#356](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/356)): `tests/conftest.py` knows `network-assessment-azure-engine 0.1.4` (model `1.5.0`), and `docs/whats-new-upstream.md` records the upstream fix (a customer's resource name containing a word such as "may" no longer stops the whole assessment; a finding that fails the hedge check is withheld and listed in `unknowns[]`) and the test the bump must rewrite. The summary line of that file now says the lab runs `0.1.3`, as its table already did.

- **Runs engine 0.1.3** ([pull request 91](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/91)): `network-assessment-azure-engine 0.1.3` (was `0.1.2`). Its only change is that the wheel ships its own `LICENSE` and `NOTICE`; rules, model and catalog are unchanged. The licence copies bundled in the image equal the wheel's byte for byte.

- **The engine wheel is the only engine; the interim port is deleted** (ADR-0006). The copy of the App's engine this
  repository carried until the wheel existed (`src/network_assessment/{model,rules,classify}`), its tests, the lab's
  own normalizer (`src/network_assessment/ingestion/normalize.py`) and `PROVENANCE.md` are removed, about 4,800
  lines. `src/network_assessment/engine.py` now imports the `network-assessment-azure-engine` wheel or stops the
  application at startup with `EngineNotInstalled` (it used to fall back to the port quietly), so the `engine` block
  of `GET /api/health` and `GET /api/rules` always names the wheel and its version (`interim-port` and a null version
  no longer occur; `docs/api/openapi.yaml` says so). Nothing an assessment returns changes: the wheel already ran,
  `docs/rules/catalog.md` is unchanged. The lab keeps its own hedge-word list and rule-text check
  (`tests/unit/test_engine.py`); two new tests prove the startup refusal, and one in
  `tests/end_to_end/test_repository_manifest.py` fails if the port or an import of it comes back. `CLAUDE.md`,
  `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `NOTICE`, the pull request template, ADR-0001 (partly superseded) and
  `docs/whats-new-upstream.md` describe the wheel-only engine.

- **The base image follows the website's current digest** ([pull request 86](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/86)): `python:3.15.2-slim-trixie` moves to `sha256:e97b88e416c3…`, the digest the website's lab image moved to on 2026-11-07 ([HCW-HybridCloudWorks#1585](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1585)), a newer build of the same Debian 13 "trixie" image. Opened by `base-update.yml`, which changes the image reference in `infrastructure/docker/versions.env` and the two `FROM` lines of `infrastructure/docker/Dockerfile`; this changelog entry was added to its pull request by hand.
- **Runs engine 0.1.2** ([pull request 87](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/87),
  [HCW-NetworkEyes_App#352](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/352)): the lab now runs
  `network-assessment-azure-engine 0.1.2` (was `0.1.1`). Application Gateway findings now read the WAF policy of each
  listener and path rule, AZ-NET-007 is at version 3 and AZ-NET-025 at version 2, and `/api/health` reports rules
  version `2026.11.0`. The tests' version pins and `docs/rules/catalog.md` moved with it, and the "Current upstream
  state" table in `docs/whats-new-upstream.md` is brought up to date (it still described the interim port).

- **Ready for engine 0.1.2** ([HCW-NetworkEyes_App#352](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/352)):
  `tests/conftest.py` knows the model version of `network-assessment-azure-engine 0.1.2` (`1.5.0`), and
  `docs/whats-new-upstream.md` records what changes upstream (WAF policies per listener and path rule; AZ-NET-007 v3,
  AZ-NET-025 v2, `RULES_VERSION` `2026.11.0`) and the version pins the bump pull request will need. Nothing changes in
  the image or the API until that bump.

- **CI lints the workflows and the Dockerfile on every pull request** ([HCW-HybridCloudWorks#1575](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1575)). The required `lint` job now ends with actionlint 1.7.12, zizmor 1.31.1 (offline) and hadolint 2.14.0 (failing at warning), the same pinned releases and SHA-256 digests as the website's CI; CodeRabbit ran these until it was removed on 2026-11-06. `.github/actionlint.yaml` declares the `ubuntu-26.04` runner label, which actionlint 1.7.12 predates.
- **The lint step's downloads retry, and its Dockerfile list cannot hide a git failure** ([HCW-HybridCloudWorks#1575](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1575)), matching the website's job ([HCW-HybridCloudWorks#1580](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1580)). The two `curl` downloads take `--retry 3 --retry-all-errors`, so a passing network error no longer fails the required job; every file is still checked against its SHA-256. The zizmor install keeps pip's own default of five retries (the website's `--retries 3` lowered it and is removed there too). hadolint's file list is written to a file before it is read, so a failing `git ls-files` stops the step instead of reading as "no Dockerfile tracked", and the pathspecs now match `Dockerfile`, `Dockerfile.*` and `*.Dockerfile` only, not any name that merely contains the word.

## [0.1.2] - 2026-11-05

This release exists so that the published image carries `apt 3.0.4`. On 2026-11-05 the website's weekly Docker Scout gate
(a scan of the images the lab host runs) failed the `v0.1.1` image for `apt 3.0.3` / `libapt-pkg7.0 3.0.3`,
CVE-2026-109518, which Debian fixed in 3.0.4 through `trixie-security`
([saulpatinojr/HCW-HybridCloudWorks#1562](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1562)). The fix,
[pull request 79](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/79), is on `main`: the `lab` stage applies
Debian's security updates in a build step of its own, with download retries off and a per-run cache bust, and a local build
proved `apt 3.0.4` inside the image. But the lab host only ever runs a published image, and only a `v*` tag publishes one,
so the fix reaches the host through this release and nothing else.

This pull request changes nothing in the lab application but the version string. What the image carries beyond
0.1.1 landed on `main` before it and is listed below: the engine adoption path (`src/network_assessment/engine.py`,
which runs the released wheel when `uv.lock` pins one and the interim port otherwise), the one additive API change
since 0.1.1, an `engine` block `{source, version}` in the `/api/health` and `/api/rules` responses (already in
`docs/api/openapi.yaml`, under `Engine`), the two-job `core-update.yml`, the base image on Python 3.15 and the daily
base-image follower. `web/` and `samples/` are unchanged since 0.1.1. The version moves from `0.1.1` to `0.1.2` in `pyproject.toml`, in `uv.lock`
(the `hcw-addon-network-assessment` entry only, re-locked with the uv CI uses, 0.11.32), in `__version__`, in
`repository.manifest.json` and in the sample output of `docs/operations/runbook.md`; `/api/health` and the
`X-Addon-Version` header read `__version__`, so they say `0.1.2`. `docs/api/openapi.yaml` keeps its document version
`0.1.0`: the `engine` block was documented there when it was added, without moving that version, and this pull request
adds no route, field or error code. Publishing the image is the tag `v0.1.2`, which is the owner's call
and is not part of this change; after it, the website's `lab-host/ansible/group_vars/all.yml` row for `network-assessment`
(still on `v0.1.0`) takes the new tag and the digest the tag run prints.

### Security
- The published image failed the website's weekly Docker Scout gate on 2026-11-05 for `apt 3.0.3` / `libapt-pkg7.0 3.0.3`
  (CVE-2026-109518, fixed in 3.0.4, published only through `trixie-security`;
  [saulpatinojr/HCW-HybridCloudWorks#1562](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1562)). The
  newest `python:3.15-slim-trixie` digest still ships 3.0.3, so no base bump could clear it. The `lab` stage's Debian
  security update is now a `RUN` of its own that fails the build when it fails (before, an unscoped `|| true` on the
  pip uninstall in the same chain swallowed a failed update or upgrade), runs `apt-get update --error-on=any` and
  `apt-get upgrade` with `Acquire::Retries=0` (the advisory needs a download retry while the base's apt is still the
  one running), and names a per-run `PUBLISH_CACHE_BUST` build argument that `publish-images.yml` and `ci.yml` pass as
  the run id and attempt, so a rebuild never reuses an older upgrade layer. A local build on 2026-11-05 carries
  `apt 3.0.4`. `tests/security/test_image_security_updates.py` pins the shape and the build arguments.

### Changed
- `.python-version` names the minor line only, `3.15` (the Makefile's `uv python pin` likewise), not the exact patch
  `3.15.1`: `actions/setup-python` with `3.15` hands out whichever 3.15.x its image carries (3.15.1 on one run, 3.15.2 on
  the next), the pinned uv 0.11.32 cannot download the other patch, and the exact pin made `uv sync --frozen` fail on
  `main` with `No interpreter found for Python 3.15.1` (run 41754320521). `requires-python` stays `>=3.15.1,<3.16`.

### Fixed
- `core-update.yml` reported the first real bump, [pull request 74](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/74) for `engine-v0.1.0`, as `compatible`
  while its catalog check had refused the wheel: the compatibility step ran `ruff && rules-doc --check && pytest` as
  one list under `set -e`, and bash does not exit on a failure inside such a list, so the refused catalog fell through
  to the browser suite and the step reported success (`pytest` never ran). Each check is now its own line;
  `tests/security/test_core_update_app_token.py` runs the step with stubbed tools that fail one check at a time and
  requires the step to fail. The engine's own differences are unchanged and recorded in `docs/whats-new-upstream.md`.
- `security.yml`'s `pip-audit` job failed on the same pull request with `Dependency not found on PyPI and could not be
  audited: cna-azure-network-engine (0.1.0)`: the engine wheel is a GitHub Release asset, so `--strict` cannot look
  it up. The export the job audits now leaves out the two engine distribution names (`--no-emit-package`); the
  engine's dependencies stay in it, `--strict` stays, and the image's own export keeps the engine.
  `tests/security/test_security_workflow.py` pins both exports.
- `core-update.yml`'s `pull-request` job could never open the bump pull request: its `uv lock --no-build` needs an
  interpreter on the Python line `.python-version` names, the job installs none (by design it runs nothing but its own
  shell and the pinned actions) and `UV_PYTHON_DOWNLOADS=never` keeps uv from fetching one, so every scheduled run since
  2026-11-03 stopped there with `No interpreter found for Python 3.15` (runs
  [41944123703](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/41944123703) and
  [41961781195](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/41961781195)). The lock now runs
  inside the base image every `FROM` of the Dockerfile pins by digest (`versions.env`), with the uv binary from the
  digest-pinned uv image mounted read-only: the CPython the add-on ships with, verified by Docker, as the runner's user,
  with no capabilities and a read-only root filesystem. `tests/security/test_core_update_app_token.py` pins that shape
  and checks that `BASE_PYTHON_VERSION` stays on the line `.python-version` names and inside `requires-python`.
- `core-update.yml` now runs from `main` only, and auto-merge no longer listens to the `bump` job's report. These are
  two High findings from a review of the same two-job workflow in the MigrateOrchestrator add-on
  ([its pull request 57](https://github.com/saulpatinojr/HCW-MigrateOrchestrator_AddOn/pull/57#discussion_r4430793870)),
  and they apply here as merged in pull requests 66 and 67.
  - Main only. A person with write access could start the workflow by hand on another branch (a manual run of
    `core-update.yml` with `--ref` set to any branch other than `main`). The checkouts already took the default branch, but
    the `pull-request` job still ran that branch's copy of the workflow's own shell before minting the App token. Now
    the first step of each job stops the run with an error that names the branch unless it was started on
    `refs/heads/main`, the `pull-request` job's `if:` also requires `main`, and both checkouts take the exact commit the
    run was started for (`github.sha`, instead of the default branch's tip, so the two jobs cannot read two different
    commits). `create-pull-request` is told `base: main`, which it needs when the checkout is a commit. The `bump` job
    has no job-level `if:` on purpose, so a refused run shows as failed rather than skipped.
  - Auto-merge. The outcome file comes from the job that ran upstream code, so a compromised release could rewrite it
    to `success`. Auto-merge now needs the repository variable `CORE_AUTOMERGE` to be `true`, a run that is not a
    probe, and the `pull-request` job's own verification; it never reads the outcome. GitHub merges only after the
    "Protect main" ruleset's required checks (`lint`, `test`, `image`, `package`, `e2e`, `rules-doc`, `pip-audit`,
    `secret-scan`, `dependency-review`) pass on the bump pull request itself. The outcome still picks the label, the
    title, the body text and the not-compatible warning, so when `CORE_AUTOMERGE` is `true` a `needs-adaptation` bump
    also has auto-merge turned on and merges once its checks pass (normally after someone fixes it on its branch);
    select **Disable auto-merge** on the pull request to hold one. `docs/whats-new-upstream.md` says so under "Trust".
  - `tests/security/test_core_update_app_token.py` checks both guards. A dated note on ADR-0004, the deletion plan in
    `PROVENANCE.md`, `VALIDATION.md`, `docs/whats-new-upstream.md` and the workflow's own comments now say the same:
    only a bump whose required checks pass merges, and the outcome picks only the label, the title, the body text and
    the not-compatible warning. Not run on GitHub yet; see `VALIDATION.md`.
- Follow-ups to the engine adoption pull request (#66), from its Copilot review: `docs/api/openapi.yaml` lists `engine` in `Health.required`, and a contract test holds the `Health`, `Engine` and `RulesResponse` schemas to the live responses. The edition-boundary test reads the engine wheel's RECORD text (`Distribution.files` silently leaves out entries whose file is missing) and allows only the package and its own `.dist-info` directory, with no `..`, absolute path or `.pth` file. A cloud SDK named in a dependency's metadata must sit behind exactly one `extra == '<name>'` marker that is false with no extra, so an `or sys_platform == …` marker can no longer slip one in. `core-update.yml` accepts the bump job's `outcome` file only when it is byte-exact. `README.md` and `VALIDATION.md` describe the armed workflow.

### Added
- The lab can run on the released engine wheel, and `core-update.yml` will open the pull request that pins it. Lab code now imports the engine only through `src/network_assessment/engine.py`, which runs the wheel (`cna-azure-network-engine`, or `network-assessment-azure-engine` from the next release) when it is installed and the interim port otherwise; `uv.lock` decides which. `pyproject.toml` carries the marker `# ENGINE_REF none`, so the workflow's next scheduled run pins `engine-v0.1.0` and opens the bump pull request with the HCW Main Admin App. Nothing changes for visitors while the port runs: the routes, responses, rule catalog and samples are the same. The wheel was compared with the port on 2026-10-31: it is **not compatible yet**, for five reasons that are fixed upstream (AZ-NET-007 and AZ-NET-025 ignore a linked WAF policy; 43 rules lack rule-level texts; two remediation texts carry a hedge word; evidence references start with `discovery:` instead of `export:`; smaller ones), so that pull request will be labelled `needs-adaptation` and will not merge: with `CORE_AUTOMERGE` set to `true` auto-merge is turned on for it too, but it waits for the required checks, which fail until the App releases a fix (`docs/whats-new-upstream.md`). New `tests/unit/test_engine.py` states what this edition needs from any engine.
- The `image` job of `ci.yml` checks that the built image runs exactly the Python that `BASE_PYTHON_VERSION` in `infrastructure/docker/versions.env` names, so a base digest that does not hold the Python it claims fails the pull request ([saulpatinojr/HCW-HybridCloudWorks#1386](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1386), "smaller things"). It also prints which engine the image runs.
- The base image now follows the website's pin by itself, so nobody has to remember to move it (issue #49). `.github/workflows/base-update.yml` runs once a day (and on demand), compares `infrastructure/docker/versions.env` with the website's `lab-image/versions.env` and, when they differ, opens one pull request that moves `versions.env` and every external `FROM` line together. A person still reviews and merges that pull request; nothing is merged automatically. How it works: the run reads the website's file at one recorded commit; `scripts/follow_website_base.py` (tests: `tests/unit/test_follow_website_base.py`) checks each value against a strict pattern, refuses a key that appears twice, and edits only those two files; before the pull request is opened, the run asks the registry whether the new digest is an index (one entry that lists every platform) with every platform the old digest had, and the pull request says whether that comparison could be made (it cannot when the registry no longer shows the old digest; then only `linux/amd64` is checked). While a pull request from the run is open and its branch already holds the website's pin, the daily run leaves it alone, so a fix a person pushed to it is not overwritten; when the website moves again the branch is rebuilt, and when the pin is no longer needed the run closes the pull request by deleting its branch. The script stops, and the run goes red with nothing opened, for a different image repository, a different Python minor line (3.14 to 3.15) or a Dockerfile it cannot move completely, because those need a person's decision; `docs/operations/runbook.md` says what to do for each. The pull request is opened by the HCW Main Admin GitHub App exactly as `core-update.yml` does it (repository variable `HCW_MAIN_ADMIN_CLIENT_ID`, repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY`, no environment), so this repository's required checks run on it, and its commit is credited to the App's bot user. `tests/security/test_base_update_workflow.py` pins that credential handling down and runs the two decision scripts against stand-ins for `docker` and `gh`; these are checks made before the first real run, which is the live proof (runbook, "Keeping the base image on the website's pin", and `VALIDATION.md`). `tests/unit/test_base_image_pin.py` fails if `versions.env` and a `FROM` line ever disagree, in the regular `pytest` run as well as in the `lint` job of `ci.yml`. `versions.env` no longer names a Python version in its header comment, because an automatic move would leave that sentence out of date. The workflow, the script and the three test files are copies, byte for byte, of the ones proved live in the Cloud Assessor add-on on 2026-10-27. Background: the website bumped its pin on 2026-10-21 and this repository's `base-follows-website` check then sat red on `main` until a person fixed it by hand ([saulpatinojr/HCW-HybridCloudWorks#1386](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1386)); that job stays as the second line of defence.

### Changed
- **Notes on the HCW Main Admin App now say it is also going on two App repositories.** On 2026-11-04 the owner
  chose to reuse the App for the lockfile workflow of `HCW-CloudCrawler_App` and `HCW-CloudAssessor_App`
  (HCW-CloudCrawler_App issue #70), so once it is installed there it covers six repositories, not four. The
  `core-update.yml` comment and `VALIDATION.md` (key rotation, where the App is installed and the accepted-risk note)
  now say so. Those two repositories use their own private key, so rotating this repository's key is unchanged.
  Comments and documentation only.
- `core-update.yml` is split into two jobs, so the HCW Main Admin App key never shares a job with upstream code. The `bump` job runs the new engine (the pin, the lock, the catalog and the compatibility check) with a read-only `GITHUB_TOKEN` and no secret, and hands over one artifact. The `pull-request` job, on a fresh runner, runs no project code and does not trust the bump job's files (code running there could have rewritten them). It works out the expected pin line itself, regenerates `pyproject.toml` and `uv.lock` from `main` (`uv lock --no-build`, with the uv binary from the image the Dockerfile pins by digest), checks that the new lock differs from `main` only in the engine's entry, and refuses the artifact unless its two copies are byte-identical to the regenerated ones. The catalog, which needs the engine to generate, is the one file taken from the artifact, and only as bounded plain Markdown with no HTML; the pull request's own drift check proves it. Only then does it mint the App token and open the pull request. The bump job's reported outcome picks the label and the body text; auto-merge also needs this job's own verification and `CORE_AUTOMERGE`, and GitHub still waits for the required checks. The wheel is chosen by its exact file name from the two known distributions, and zero or several matches fail the run. `tests/security/test_core_update_app_token.py` pins the design down.
- `GET /api/health` and `GET /api/rules` gain an additive `engine` block, `{source, version}`, which says whether the port or the wheel (and which version) answers. The envelope stays flat, and the status proxy reads nothing new (`docs/website-integration/integration-guide.md`, `docs/api/openapi.yaml`). A test fails when the engine that runs is not the one the `ENGINE_REF` line names, and the `image` job of `ci.yml` makes the same comparison inside the built image.
- `tests/security/test_edition_boundary.py` also reads the installed engine wheel: its imports, endpoints and credential names (all but its `discovery/` live-discovery extra), and its installed files (no `.pth` file, nothing outside its own package). A fresh-process test runs an assessment through the API and checks that no cloud SDK and no `discovery` module was loaded. `adal` and the exact name `azure` join the refused names, and `[project.optional-dependencies]` is checked for extras too. `tests/unit/test_engine.py` lists the hedge words this edition requires and fails if the running engine's enforcer stops flagging one.
- `core-update.yml` reads the wheel's file name from each engine release and rewrites the whole `ENGINE_REF` line, so the first release is pinned under its own (earlier) name and later releases under the new one; it accepts the marker `none` for the first adoption, regenerates `docs/rules/catalog.md` and commits it with `pyproject.toml` and `uv.lock`. `pyproject.toml` sets `[tool.hatch.metadata] allow-direct-references = true`: without it the build refuses the URL pin, so no bump could ever have built.
- `tests/security/test_edition_boundary.py` reads `uv.lock` as data instead of matching text: it refuses any locked cloud SDK package, any dependency on one, any extra requested in `pyproject.toml`, and any cloud SDK named in a dependency's metadata other than behind an extra. The engine wheel names the Azure SDKs of its `[azure]` live-discovery extra in its metadata; this edition never asks for that extra and nothing of it is locked or installed (the image build checks the same).
- `core-update.yml` follows the App's rename of its engine package (the App's pull request for step 4 of the rename of its short code name): the package is `network-assessment-azure-engine`, the wheel file name is `network_assessment_azure_engine-<version>-py3-none-any.whl`, and the bump commit message says so. It stays inert until an `ENGINE_REF` line exists. The README diagram, `PROVENANCE.md` and `docs/whats-new-upstream.md` say the same; statements about the published `engine-v0.1.0` keep the old name, because its files do. No code and no image changed.
- The base image and the Python line move to the website's `python:3.15.2-slim-trixie` pin (Python 3.15), so the
  `base-follows-website` job of `security.yml` is green on `main` again
  ([saulpatinojr/HCW-HybridCloudWorks#1386](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1386)). The
  website moved its `lab-image/versions.env` to Python 3.15 on 2026-10-31
  ([its pull request 1468](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1468)); the daily `base-update.yml`
  run refuses a move between Python minor lines by design ("a person must decide", `scripts/follow_website_base.py`), so
  this is that decision, made by hand in one pull request as `docs/operations/runbook.md` says. Everything that names the
  line moved together: `BASE_IMAGE`, `BASE_DIGEST` and `BASE_PYTHON_VERSION` in `infrastructure/docker/versions.env`
  (`python:3.14.8-slim-trixie@sha256:fbecd461...`, 3.14.8, to `python:3.15.2-slim-trixie@sha256:8c13a3f3...`, 3.15.2);
  both `FROM` lines and the four `python3.14` paths in `infrastructure/docker/Dockerfile`; `requires-python` in
  `pyproject.toml` (`>=3.14.6,<3.15` to `>=3.15.1,<3.16`; the floor is the 3.15 that GitHub's runners carry, below the base as before); `.python-version`, the `setup` target of the `Makefile` and
  the README's quick start (`uv python pin 3.15.1`); `PYTHON_VERSION` in `ci.yml` and `python-version` in
  `security.yml` and `core-update.yml` (`3.14` to `3.15`); and `uv.lock`, re-resolved for CPython 3.15 with the uv CI
  uses (0.11.32): no package version changed, only the wheel lists, and every package with a compiled wheel
  (pydantic-core, charset-normalizer, coverage, msgpack, tomli) has one for CPython 3.15 on PyPI, so nothing is built from
  source. The runbook's table, the script's docstring and `base-update.yml`'s comment now give the next move (3.15 to
  3.16) as their example. The `image` job of `ci.yml` already compares `python --version` in the built image with
  `BASE_PYTHON_VERSION`, so a digest that is not the Python the line says fails there. Checked on the owner's Windows
  workstation: the image builds on the new base, runs Python 3.15.2, keeps its edition boundary and licence label, answers
  `/api/health` and accepts the sample export; 496 tests pass at 97 percent coverage; the `lint` job's `FROM` check, the
  `base-follows-website` comparison and `scripts/follow_website_base.py --check` (`changed=false`) all pass against the
  website's current file. Playwright was not run here; see `VALIDATION.md`.

## [0.1.1] - 2026-10-27

This release exists so that the published image states its open-source licence. The Dockerfile has set the image label
`org.opencontainers.image.licenses=MIT` since [pull request 47](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/47) (a label is a line of text stored inside
the image that registries and scanners read), but a label reaches Docker Hub only when a release tag is pushed. The images
published so far (`v0.1.0`, `0.1.0` and the release candidate `v0.1.1-rc.1`) were built without it, so this is the first
image that carries it (issue [50](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/issues/50)).

The lab application itself does not change. `src/`, `web/` and `samples/` are the same as in 0.1.0 except for the version
string, so the routes, settings, rules and responses are as before. What changed since 0.1.0 is how the image is built and
kept up to date, the workflows around it, the Coder template and the documents, as listed below. The version moves from
`0.1.0` to `0.1.1` in `pyproject.toml`, in `uv.lock` (the `hcw-addon-network-assessment` entry only), in `__version__`, in
`repository.manifest.json` and in the sample output of `docs/operations/runbook.md`; `/api/health` and the
`X-Addon-Version` header read `__version__`, so they say `0.1.1`. `docs/api/openapi.yaml` keeps its document version
`0.1.0`, because no route, field or error code changed. The image was published on 2026-10-27 by the tag `v0.1.1` (digest
`sha256:338e0e035d053b918f6840bab6eb5871eb739f4d132a076d9497fec54a162635`;
[release](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/releases/tag/v0.1.1)).

### Changed
- A manual run of the publish workflow (`publish-images.yml`) is now a true dry run: it builds, checks and scans the image but never pushes, because only a `v*` tag does. Before, the gate step looked only at the repository variables, so a manual run on `main` went on to the Docker login ([pull request 51](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/51)).
- `core-update.yml` opens its bump pull request with a short-lived GitHub App token (`actions/create-github-app-token`, pinned to v3.3.0; the HCW Main Admin App, installed on this repository: its client ID is the repository variable `HCW_MAIN_ADMIN_CLIENT_ID`, which is not a secret, and its private key is the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY`, which is never printed; the job no longer runs in an environment) instead of `GITHUB_TOKEN`. The token step names this repository (`repositories: ${{ github.repository }}`) and sets no `owner`, so even an empty value could only fall back to this repository, never to every repository the App is installed on. Why: a pull request opened with `GITHUB_TOKEN` starts no workflow, so the required checks of the `Protect main` ruleset would never run on it and it could not merge. The token is minted for this repository only, with Contents and Pull requests write, after the compatibility check and just before the pull request is opened; `GITHUB_TOKEN` is now `contents: read` only. Because the App's pull request starts this edition's own CI, the "do not trigger other workflows" comment is gone; the compatibility check in the run still decides the label (since the main-only entry under Fixed, it no longer decides whether auto-merge is requested). Turning on auto-merge no longer fails the run when the repository setting "Allow auto-merge" is off; it warns and leaves the pull request to merge by hand. A manual run with `probe=true` mints the token, makes a read-only call and lists the repositories the token covers (the run fails unless that is this repository only), and opens no pull request and asks for no auto-merge even when a newer release exists, to prove the credential while the workflow is still inert (no `ENGINE_REF` line yet). `tests/security/test_core_update_app_token.py` pins all of it (no `GITHUB_TOKEN` passed to `create-pull-request`, the token step first, the HCW Main Admin variable and secret, the token limited to this repository, exactly the two permissions, SHA pins, and none of the old credential names left). To rotate the key, generate a new private key on the settings page of the App (https://github.com/settings/apps), replace the repository secret `HCW_MAIN_ADMIN_PRIVATE_KEY` in every repository that holds the key (this one: https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/settings/secrets/actions; the App is installed on the four add-on repositories, so check the other three), then delete the old key on the settings page of the App. The settings page can hold several keys, so a separate key per repository lets you revoke one without touching the others.
- The lab image repository on Docker Hub is renamed from `hybridcloudworks/hcw-addon-network-assessment` to `hybridcloudworks/img-ne-lab-addon` (owner naming convention `img-<short name>-<job>-<type>`, 2026-10-25), and its tag is now the full release tag (`v0.1.0`, not `0.1.0`). `publish-images.yml` (`IMAGE`, the tag, the image title label), the local `:dev` build tag, the README and the deployment and integration documents follow. The container name on the lab host (`hcw-addon-network-assessment`) is **not** changed: the website's host role owns it. Nothing is published by this change; the next `v*` tag pushes to the new name once the Docker OIDC connection allows it (`docs/deployment/lab-host.md`, step 4).
- Hardening: the last step of `publish-images.yml` printed the release version straight into a shell command (`echo "image_tag: ${{ steps.version.outputs.version }}"`). The version comes from the pushed tag's name, so a crafted tag name could inject a command. It now reaches the shell through the environment variable `IMAGE_TAG` and is printed as `"${IMAGE_TAG}"`. This was already present before the rename; only people with write access can push tags.
- `docs/website-integration/integration-guide.md` follows the website after hybridcloudworks.com#1359 (issues #1353 and #1354, owner decisions of 2026-10-24): the row now holds `downloads` and `clipboard-write` (it held `navigate` and `downloads`), the frame address carries `?theme=dark|light` read once from the site's theme, the clipboard grant is write only, and the row copy is taken from website commit b0cf0055.
- `docs/website-integration/integration-guide.md` now follows the website's real catalogue row. The row pasted into it was
  written before the row shipped and had drifted: 6 of its 10 fields differed from the website's (title, summary, pane
  path, technology, status and capabilities, plus the `comingSince` and `comingReason` fields). The block is now a copy
  of the website's current row, with the website commit it came from, and says the website is the authority. The guide
  also says that the site frames `origin + panePath` with no `?theme=` parameter (the pane still honours one), and that
  the site grants `navigate` and `downloads` where this AddOn asked for `downloads` and `clipboard`; the owner confirms
  whether that is intended. Compared field by field with a script on 2026-10-24: 0 of 10 now differ.
- `.github/dependabot.yml` groups `pydantic` and `pydantic-core` so they arrive in one pull request. pydantic requires one exact `pydantic-core`, so a `pydantic-core` bump on its own cannot resolve; the same failure closed the App repository's Dependabot pull requests.
- Dependency updates pass CI as Dependabot opens them. Its `pip` updater rewrote `pyproject.toml` and the committed
  `requirements.lock.txt` but never `uv.lock`, so every one of its pull requests failed the export check (#16 to #19).
  `.github/dependabot.yml` now uses the `uv` ecosystem, which moves `pyproject.toml` and `uv.lock` together. The
  committed export is gone: the image's build stage runs `uv export --frozen` from `uv.lock` with the uv CI uses, by
  digest, and still installs with `pip --require-hashes --no-deps`; uv never reaches the lab stage. CI checks
  `uv lock --check` and that the Dockerfile's uv is `UV_VERSION`; `pip-audit` audits the same export.
- Base image `python:3.14.8-slim-trixie` by digest, the website's current pin (CONTRACT-DECISIONS item 20). There is
  no docker Dependabot entry: the base follows the website, and the uv image follows `UV_VERSION`. CI builds the
  image on every pull request, resolves the uv digest for `UV_VERSION` rather than trusting any digest, and a weekly
  job flags the base drifting from the website's pin.
- The base image digest follows the website's current pin again (`python:3.14.8-slim-trixie@sha256:fbecd461...`, same
  tag, newer build; `versions.env` and both `FROM` lines). The website rebuilt on it on 2026-10-21; `security.yml`'s
  `base-follows-website` job, which runs on `main` and weekly only, had been red on `main` since its first run after
  that (2026-10-24). An image built from the next tag uses the current base; a tag already published keeps the base
  it was built on.
- The lab image states its open-source licence in the form registries and scanners read.
  `infrastructure/docker/Dockerfile` sets `org.opencontainers.image.licenses="MIT"` on the final stage (the SPDX id
  of `LICENSE`, the MIT License). The `image` job in `ci.yml` fails when the built image lacks the label or `LICENSE`
  stops being MIT, and the pre-publish check in `publish-images.yml` fails when the image about to be pushed lacks it.
  The `labels:` input of `publish-images.yml` must not set this label: it would override the Dockerfile's. The image
  tags on Docker Hub on 2026-10-26 (`0.1.0`, `v0.1.0` and `v0.1.1-rc.1`) were built without the
  label and are not changed; the label reaches Docker Hub with the next tagged release, which is `v0.1.1`.
- Dependencies moved to newer releases through Dependabot (between 2026-10-16 and 2026-10-24). In the image: fastapi
  0.143.0 to 0.156.8 ([34](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/34)), starlette 1.7.0 to 1.9.0 ([24](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/24), [29](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/29)), pydantic 2.14.0 to 2.14.1 with
  pydantic-core 2.50.0 to 2.50.1 ([25](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/25)); uvicorn stays at 0.54.0. Development only, not in the image: ruff 0.17.1
  ([26](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/26)), certifi 2026.10.19 ([28](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/28)), filelock 4.2.4 ([23](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/23), [36](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/36)), pip 26.2.2 ([30](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/30)), platformdirs
  4.13.5 ([22](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/22), [35](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/35)) and pluggy 1.7.0 ([27](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/27)).
- The Coder template (`infrastructure/coder/template/main.tf`, pushed to Coder by `coder-template.yml`; it is not part of the
  image) had two fixes after 0.1.0. [14](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/14): `assessment_id` gets a placeholder default (all zeros) and `bundle_token` gets an
  empty default and can be changed, so that `coder templates push` accepts the template (the reason the commit gives).
  [15](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/15): the parameter values reach the workspace start-up script as agent environment variables instead of being pasted
  into the script text, the bundle download runs only when a token and a real assessment id are present, and the template's
  one `local.default_image` replaces a second copy of the workspace image digest.
- README: the "Where to try it" paragraph no longer says the pane will appear once the first image is published (the website
  lists the tool as available and its status route answers), and "Releases and artifacts" no longer says the push is
  skipped until the Docker connection is enabled (both repository variables are set, and `v0.1.0` and `v0.1.1-rc.1` were
  pushed).

### Added
- `.github/workflows/guide-drift.yml` switches on the website's check that this repository's integration guide still says what the website says (website issue saulpatinojr/HCW-HybridCloudWorks#1356). It calls a reusable workflow (a workflow that another repository can call, like a function) from the website repository, pinned to a full commit, and compares the catalogue row pasted into `docs/website-integration/integration-guide.md` with the website's row for `network-assessment`, field by field. It runs on pull requests that touch the guide or this workflow, every Monday at 06:35 UTC and on demand. It holds no secret and has `contents: read` only. To switch it off, delete the file. How to read a failure: https://github.com/saulpatinojr/HCW-HybridCloudWorks/blob/main/docs/runbooks/addon-guide-drift.md
- **`docs/whats-new-upstream.md`**: the running record of what changed in the App and what this edition has to do about it, with the state of the engine release (`engine-v0.1.0`, published 2026-10-12, not adopted yet) and the adoption steps. `CLAUDE.md`, `AGENTS.md`, `README.md`, `PROVENANCE.md`, `VALIDATION.md` and `infrastructure/README.md` no longer say the wheel is still to be published. Listed in `repository.manifest.json`.

## [0.1.0] - 2026-10-11

The first release: the tag `v0.1.0`, commit `9a60477`. The entries below are the ones in this file at that tag, unchanged;
everything added to this file afterwards is under 0.1.1 above.

### Changed
- Repository hygiene: `.github/dependabot.yml` groups GitHub Actions updates under `all-actions` and removes the unused `/tests/e2e` npm entry; `infrastructure/docker/Dockerfile`, `README.md`, and `CLAUDE.md` updated to match `HCW-NetworkEyes_App` and `ADR-0005`.
- README: a "where to try it" paragraph for new visitors; the diagram says the engine wheel is attached to each `engine-v*` release of the App. `core-update.yml`'s checkout no longer persists credentials (two Authorization headers made GitHub answer `400` to `create-pull-request`'s push in the Migrate App's `rules-refresh`).
- **Upstream is `saulpatinojr/HCW-NetworkEyes_App`** (owner decision 2026-10-10: the Core lineage was merged back into the App, which now holds the engine package and its `engine-v*` releases). `core-update.yml` watches that repository and pins the engine as the GitHub Release wheel asset by URL, so `uv lock` records its sha256 and the image's `pip install --require-hashes` keeps verifying it (a git+https pin cannot be hash-checked); no PyPI step is needed for adoption. Provenance headers, `PROVENANCE.md`, the governance files and the docs name the App; ADR-0001 and ADR-0004 carry an amendment note.

### Added
- **Always-on guided workspace handoff (ADR-0005):** `POST /api/assessments/{assessment_id}/workspace` (`202 Accepted`) issues a single-use, 10-minute `x-bundle-token` (`AssessmentStore.issue_bundle_token` / `redeem_bundle_token`) scoped to `GET /api/assessments/{assessment_id}/bundle.zip` and returns a workspace launch descriptor (`CoderWorkspaceProvider` in `src/network_assessment/workspace.py`). Supports both direct upstream API provisioning (when `CODER_SESSION_TOKEN` is set) and browser-session auto-create deep links (`https://coder.lab.hybridcloudworks.com/templates/na-guided-lab/workspace?mode=auto&...` by default). `/api/health` and `/api/config` report `"workspace": "coder"` and `"workspace"` in `CAPABILITIES`. Added `#open-workspace` ("Open in lab workspace") to `web/index.html` and `web/app.js`, the ADR-0032 / LAB-5 hardened Linux container Coder template `infrastructure/coder/template/main.tf` (`tcp://coder-docker-proxy:2375`, `user = "65534:65534"`, `HOME = "/tmp/home"`, `module "code-server"` with `subdomain = true`, `/usr/local/libexec/hcw-boot/hcw-boot network-assessment` + `python3 -m zipfile -e`), `.github/workflows/iac-validate.yml`, `.github/workflows/coder-template.yml`, `docs/deployment/coder.md`, and `docs/adr/ADR-0005-always-on-guided-workspace-handoff.md` (with appliance team handoff notes; core engine under `src/network_assessment/{model,rules,classify}` untouched).
- Code scanning: the e2e host page accepts only a loopback `?addon=` origin for the frame and the message filter, and the unit test asserts the exact `script-src` and `frame-src` source lists instead of a substring (closes the three CodeQL alerts raised on #5; test and harness code only, no runtime change).
- Interim ported engine (ADR-0001, `PROVENANCE.md`) from `saulpatinojr/HCW-NetworkEyes_App` at `5d3b914`: the
  observed-state enforcer (verbatim), the trimmed findings model (`ObservedState.state`, `remediation`, `learn_url`,
  `rule_version`), the lab topology model `lab-1.0.0` (26 Azure classes plus `AzureFirewallPolicy`,
  `AppGatewayWafPolicy`, `FlowLog`), the topology classifier, the traffic-direction taxonomy and the framework
  mappings as data.
- Rule registry (`@rule`, `RULES`, `RULES_VERSION = "2026.10.0"`, `evaluate()` with `rule_id:resource_id` dedup and the
  enforcer on every fact): AZ-NET-001..007, 011 (re-derived from `ipConfigurations`), 012, 014, 018 ported from Engine A;
  AZ-NET-020..033 ported from Engine B as typed rules; AZ-BCDR-001..005 ported plus 006/007; AZ-COST-001/004 ported
  without the price table; AZ-NET-008/009/010/013/015/016/017/019 and AZ-COST-002/003/005 registered live-only and
  reported in `unknowns[]`. `docs/rules/catalog.md` generated by `scripts/rules-doc.py` with a CI drift check;
  `GET /api/rules` serialises the registry.
- Ingestion: JSON array or `az graph query` envelope (BOM strip, paged warning), Resource Graph Explorer CSV with JSON
  cells, the portal "All resources" CSV accepted with the "no properties column" warning (property rules answer
  unknown); 5 MB / 5,000-row caps; `invalid_export` for anything that is not an export; the normalizer maps ~20
  `microsoft.network/*` types onto the model, resolves references by id within the export, warns on unresolved ones,
  counts network interfaces and lists unmapped types.
- Lab application `src/network_assessment` 0.1.0 (FastAPI 0.143.0, uvicorn 0.54.0, pydantic 2.14.0): `NA_*` settings
  (numeric settings bounded by `MAX_SETTING`), import-time edition guard, in-memory store, human verification with
  `action` echo and `NA_PUBLIC_HOST` hostname binding, fail-closed posture (`NA_ALLOW_NO_TURNSTILE=1` local only),
  security headers with configurable `frame-ancestors`, exact-origin CORS, streamed body cap, per-client token bucket
  (`NA_TRUST_PROXY` for `X-Forwarded-For`), concurrency bound (`503 overloaded`), content-free JSON logs, the flat
  `/api/health` envelope with `rules`, `model` and `limits`, and the documented route set with the error envelope.
- Outputs: summary (counts, topology pattern, findings by severity, unknown rules, versions), `findings[]`,
  `resources[]` with the facts the rules read, `unknowns[]`, `report.md`, `report.json`, `bundle.zip` (README.md,
  report.md, findings.json, topology.json, summary.json, rules.json, NOT-FOR-PRODUCTION.md).
- Vanilla pane (`web/`) with the HCW theme tokens, `?theme=` selection, the `hcw-addon` message bridge
  (`loading | ready | working | unavailable`), upload preview, summary tiles and topology pattern, findings table with
  severity and category filters, resource detail drawer, unknowns panel, "What this cannot tell you" panel, report and
  resources tabs, bundle download, "Copy report" fallback, immediate delete and the expiry line.
- Samples (48 fictional rows in two subscriptions, three export shapes) designed so every portable rule fires; results
  pinned in `tests/unit/test_sample_expectations.py`; unit (incl. ported rule tests), contract (OpenAPI two-way),
  security (edition boundary, no secrets, content-free logs), manifest/provenance and Playwright suites.
- Docs (website integration, routes, API, lab host, appliance pointer, runbook, threat model incl. the host identity
  endpoint, user guide with the owner-pasteable export commands, bundle, generated rule catalog, ADR-0001..0004),
  hardened two-stage Dockerfile on the website's base-image digest, local compose, SHA-pinned `ci`, `security`,
  `publish-images` (Docker Hub by OIDC, Trivy before push, image-level boundary check) and inert `core-update`
  (watches the Core's `engine-v*` releases) workflows, Dependabot, CODEOWNERS, PR template.
