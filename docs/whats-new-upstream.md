# What's new upstream

This lab edition is built from the engine in `saulpatinojr/HCW-NetworkEyes_App` (the "App"). This file is the
running list of what changed there and what, if anything, this repository has to do about it.

## How to use this file

Read it before you change behaviour here, and read the **Current upstream state** table first: it says in plain words
which version of the App's engine this repository really runs. When you adopt an upstream change, or decide one does
not matter, add or edit an entry in the same pull request so the next person (or the next Claude session) does not
have to rediscover it.

## Current upstream state

Checked on 2026-11-09 against the App's releases and tags, while adopting `engine-v0.1.5`
([pull request 97](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/97)).

| Question | Answer |
|---|---|
| App commit of the latest engine release | `4512991`, the commit the tag `engine-v0.1.5` points at (the merge of [HCW-NetworkEyes_App#376](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/376)). Update this row when you adopt something. |
| Latest engine release | **`engine-v0.1.5`**, published 2026-11-09 by `320-release-engine.yml` ([run 42558376865](https://github.com/saulpatinojr/HCW-NetworkEyes_App/actions/runs/42558376865), success; PyPI publishing skipped, as before). [Release page](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.5). |
| Its files | `network_assessment_azure_engine-0.1.5-py3-none-any.whl`, sha256 `689d15be41006ea48710f96cc7ca93e039dffde9c5a54d5f03b4db5f2824fdbc` (the digest on the release page, the one `uv.lock` records, and the sha256 of the downloaded file), and `network_assessment_azure_engine-0.1.5.tar.gz`, sha256 `3aba83d7c3856590968ab8ac3a6538aaf0a993fc818f0892ed1a0c455d52034d`. |
| Engine package name | Distribution `network-assessment-azure-engine`, import name `network_assessment_azure_engine`, since the App renamed the package on 2026-10-27 (`engine-v0.1.0` was published as `cna-azure-network-engine`). `core-update.yml` knows both names. |
| Other App tags | `v0.1.0` and `v0.8.0` (application releases from the App's earlier history, not the engine). The engine tags are `engine-v0.1.0` to `engine-v0.1.5`. |
| What this repository runs | **The wheel**, `network-assessment-azure-engine 0.1.5`, pinned by URL in `pyproject.toml` (`# ENGINE_REF 0.1.5`) and by sha256 in `uv.lock`; `src/network_assessment/engine.py` runs it. The wheel was first adopted at `0.1.1` ([pull request 78](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/78)). **It is the only engine**: the interim port under `src/network_assessment/{model,rules,classify}`, the lab's own normalizer and `PROVENANCE.md` were deleted on 2026-11-08 (ADR-0006), and `engine.py` refuses to start without the wheel. |
| `core-update.yml` | Opens one bump pull request per new `engine-v*` release, with the HCW Main Admin App. The `engine-v0.1.5` bump is [pull request 97](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/97). |
| Version markers | `RULES_VERSION` `2026.11.1` (was `2026.11.0` until 0.1.5), `TOPOLOGY_MODEL_VERSION` `1.5.0` (`MODEL_VERSIONS` in `tests/conftest.py`; the registry digest is pinned in `tests/unit/test_engine.py`). The port's `2026.10.0` and `lab-1.0.0` left with the port. |
| Is `engine-v0.1.5` compatible? | **Yes, with the rule pins moved.** `RULES_VERSION` is `2026.11.1` and the registry digest `715d1fdd…ffed1` (both pinned in `tests/unit/test_engine.py`; the digest matches the value computed upstream). The other pins of `2026.11.1` are in `test_api.py`, `test_report.py`, `test_sample_expectations.py` and the browser test `tests/e2e/lab.spec.ts`. `TOPOLOGY_MODEL_VERSION` stays `1.5.0`; no sample finding is withheld. |

In short: this repository runs the App's engine wheel, now at `0.1.5`, and nothing else: the interim port is gone.
Every engine change from here on is made in the App, released, and arrives through a `core-update.yml` bump.

## Entries, newest first

### 2026-11-14: the workflow runtime check moves to round four (website [#1725](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1725), NetworkEyes_App [#403](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/403))

- The check that every workflow step running Python or Node.js sets its version up first has a fourth round: it
  reads `coproc`, reads a step's `shell:` as the runner passes it on (no shell fills in `$PATH` there), treats a
  `shell:` holding a GitHub expression it cannot read as able to run either runtime, and holds Python to 3.15.2, the
  newest 3.15 release. Its canonical copy is the Python one in HCW-NetworkEyes_App
  ([HCW-NetworkEyes_App#403](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/403), open when this was written); the website's JavaScript twin merged
  in [HCW-HybridCloudWorks#1725](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1725). This repository's `tests/security/test_workflow_runtime_setup.py` is refreshed from the
  canonical copy in the same pull request as this entry; only its own lists stay its own.
- **Reaches this edition? Only as this test.** No engine, catalog, rule, wheel or release change comes with it, so
  `core-update.yml` has nothing to adopt. The App (HCW-NetworkEyes_App) holds the canonical copy, so it has the change in that pull request.
- What the test now reads is in this repository's `CHANGELOG.md` entry of the same date.

### 2026-11-14: the workflow runtime check takes Copilot's second round on the round-3 copies (website [#1723](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1723), NetworkEyes_App `85fe01c`)

- Copilot's second review round on the round-3 copies of the check (the test that every workflow step running Python or
  Node.js sets its version up first) found six more ways past it. They were fixed first in the canonical Python copy in
  HCW-NetworkEyes_App (commits `55e94dd` and `85fe01c` on its branch `claude/runtime-copilot-r2-1707`) and in the
  website's copy, merged in [HCW-HybridCloudWorks#1723](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1723).
  This repository's `tests/security/test_workflow_runtime_setup.py` takes them in the same pull request as this entry;
  only its own lists stay its own.
- **Reaches this edition? Only as this test.** No engine, catalog, rule, wheel or release change comes with it, so
  `core-update.yml` has nothing to adopt. The App (HCW-NetworkEyes_App) holds the canonical copy, so it already has the
  change.
- What the test now reads is in this repository's `CHANGELOG.md` entry of the same date.

### 2026-11-14: the App and this repository both require Python 3.15.2 (owner decision)

- The owner decided on 2026-11-14 that every Hybrid Cloud Works Python repository requires the latest stable release
  of Python 3.15, which is 3.15.2 (released 2026-10-25). The App, in [HCW-NetworkEyes_App#401](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/401),
  moves `requires-python` from `>=3.14` to `>=3.15.2,<3.16` in both of
  its `pyproject.toml` files, including the engine `network-assessment-azure-engine`; its unit tests stop running on
  Python 3.14 (TODO.md T-743 item 4 there), ruff targets `py315`, and `uv.lock` is re-locked with uv 0.13.8 (no
  package version moved). Its wheel test now expects `Requires-Python: <3.16,>=3.15.2`. This repository makes the same
  move in its own pull request: `requires-python` `>=3.15.2,<3.16`, re-locked.
- **What reaches this repository:** the engine's `Requires-Python`, at the next `engine-v*` release. That wheel will
  not install on Python 3.14, 3.15.0 or 3.15.1, and for the first time it names a ceiling (`<3.16`). This repository
  then requires the same range and runs 3.15.2 (`infrastructure/docker/versions.env`), so `core-update.yml` adopts it
  as usual and `tests/security/test_engine_static_metadata.py` (the wheel accepts every Python the project allows)
  stays green. The `engine-v0.1.5` pin (`Requires-Python: >=3.14`) is unaffected.
- Not checked: the App's next engine release, which is not tagged yet.

### 2026-11-14: the workflow runtime check moves to round three here and in the App (website [#1722](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1722), NetworkEyes_App [#399](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/399))

- The check that every workflow step running Python or Node.js sets its version up first has a third round of rules
  (the list on [HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707), plus the fixes
  from its review). Its canonical copy is the Python one in HCW-NetworkEyes_App
  ([HCW-NetworkEyes_App#399](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/399), merged); the website's
  JavaScript twin merged in [HCW-HybridCloudWorks#1722](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1722).
  This repository's `tests/security/test_workflow_runtime_setup.py` is refreshed from the canonical copy in the same
  pull request as this entry; only its own lists stay its own.
- **Reaches this edition? Only as this test.** No engine, catalog, rule, wheel or release change comes with it, so
  `core-update.yml` has nothing to adopt. The App (HCW-NetworkEyes_App) already has it: its copy is the canonical one,
  merged in [HCW-NetworkEyes_App#399](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/399).
- Copilot's review of these pull requests found six more ways past the check, and a review of those fixes one more
  (a `sudo` inside a script `sudo` runs, a PATH replaced or removed for one command, the runner's interpreter named
  directly, one-line `case` clauses, `${{ matrix.* }}` in the workflow-level `env:`, pipx under a step's `shell:`,
  and free-threaded Python names such as `python3.14t`); they were fixed in the canonical copies first and are in
  this repository's copy in the same pull request, still with nothing to adopt.
- What the test now reads is in this repository's `CHANGELOG.md` entry of the same date.

### 2026-11-13: the App builds the engine with uv 0.13.8

- The App's `320-release-engine.yml` (the workflow that builds and publishes the engine wheel this repository installs)
  and its `300-test-codebase.yml` now install uv 0.13.8 instead of 0.13.7, to match the App's Dockerfiles, which
  Dependabot had already moved to 0.13.8. The App's change is
  [pull request 398](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/398). It also adds a test there that fails when a workflow's uv differs from the
  Dockerfiles' uv. ([HCW-HybridCloudWorks#1707](https://github.com/saulpatinojr/HCW-HybridCloudWorks/issues/1707))
- **Does the engine wheel change?** No. The engine `0.1.5` source was built with uv 0.13.7 and with uv 0.13.8 (the
  same setuptools 84.2.1 and wheel 0.48.0 backend both times). With the same `SOURCE_DATE_EPOCH` (a fixed build date)
  the two wheels are byte-identical; without it they hold the same 31 files with the same contents and differ only in
  the build-time dates inside the zip, which also differ between any two builds with the same uv. The sdists hold the
  same files and contents and differ only in those dates.
- **Reaches this edition? Not by itself.** No engine release comes with it, so `core-update.yml` has nothing to adopt.
  The next `engine-v*` release is built with uv 0.13.8 and arrives through `core-update.yml` as usual. This repository
  moves its own uv to 0.13.8 in the same change set as this entry (see `CHANGELOG.md` and `VALIDATION.md`).

### 2026-11-13: the workflow runtime check moves to round two here and in the App

- The check that every workflow step running Python or Node.js sets its version up first has a second round of rules.
  Its canonical copy is the Python one in HCW-NetworkEyes_App
  ([HCW-NetworkEyes_App#395](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/395)); the website's JavaScript
  twin merged in [HCW-HybridCloudWorks#1719](https://github.com/saulpatinojr/HCW-HybridCloudWorks/pull/1719). This
  repository's `tests/security/test_workflow_runtime_setup.py` is refreshed from the canonical copy in the same pull
  request as this entry; only its own lists stay its own.
- **Reaches this edition? Only as this test.** No engine, catalog, rule, wheel or release change comes with it, so
  `core-update.yml` has nothing to adopt. The App (HCW-NetworkEyes_App) already has it: its copy is the canonical one,
  changed in [HCW-NetworkEyes_App#395](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/395), which was waiting
  for the owner's merge when this was written.
- What the test now reads is in this repository's `CHANGELOG.md` entry of the same date.

### 2026-11-09: engine 0.1.5 adopted; rule notes are checked for hedge words

- **Released.** `engine-v0.1.5` was published on 2026-11-09
  ([release](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.5)) from `4512991`.
  `core-update.yml` opened [pull request 97](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/97).
- **One more change than the entry below expected.** After that entry was written, the App pull request also reworded
  `AZ-NET-009` so its title and descriptions match what the rule checks (zero rule hits **or** zero data processed):
  the title is now "Azure Firewall with no rule hits or no processed data" and the description says what Azure
  Monitor reported. So `docs/rules/catalog.md` changes the `AZ-NET-009` title and description too, not only the two
  version cells and the provenance line. The registry digest does not include titles, so it is as predicted.
- **What this repository changed.** The rule pins moved to `2026.11.1` and digest `715d1fdd…ffed1` (the table above
  lists the files), and the catalog was regenerated. Nothing in the lab's own code changed: it passes no customer
  values to the engine, so the stricter type check never fires here.

### 2026-11-08: engine 0.1.5 is prepared upstream: rule notes are checked for hedge words

- **What changes upstream.** [HCW-NetworkEyes_App#376](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/376)
  (open when this entry was written; issue
  [HCW-NetworkEyes_App#364](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/364)) moves the package version
  to `0.1.5` and makes four changes:
  1. When a rule is registered, its remediation and the note on each framework mapping (the `alignment` field) are now
     checked for hedge words, as the title and description already were. Two notes failed and are reworded to state
     what was observed: `AZ-NET-009` "Zero rule hits suggests traffic bypasses the firewall" becomes "Zero rule hits or
     zero data processed in 24 hours was observed on the firewall" (the rule fires on either), and `AZ-NET-019` "App Gateway capacity degradation indicates resilience
     gap" becomes "App Gateway backend latency or failure rate above the threshold is a resilience gap". **Both rules
     move to version 2, and `RULES_VERSION` moves from `2026.11.0` to `2026.11.1`.** What the rules find does not
     change.
  2. `ObservedStateEnforcer.scan_text` and `validate`, and the registry's `evaluate_subscription`, raise `TypeError`
     when the customer identifiers are passed as one plain string instead of a collection (a string is a collection
     of its characters). This repository passes none: its only call, in `src/network_assessment/engine.py`, passes no
     customer values.
  3. A test upstream fails when a rule's own text glues a hedge word to a customer value (`f"{name}-may"`), which a
     customer identifier could otherwise excuse. Nothing here changes for it.
  4. Evaluation also checks the remediation and framework notes a rule sets on a finding itself (a rule's own
     `recommendation`, or a finding it builds with its own mappings); a hedged one is withheld into `unknowns[]`.
     No current text hedges, so the samples are not expected to gain an unknown (the bump's
     `test_samples_have_no_finding_withheld_for_hedged_wording` would say so).
- **What this repository did meanwhile.** `tests/conftest.py` knows `network-assessment-azure-engine 0.1.5`
  (model `1.5.0`, unchanged) in `MODEL_VERSIONS`; the row is unused until the bump.
- **What the bump to 0.1.5 needs.** Once the owner pushes the `engine-v0.1.5` tag on the App, `core-update.yml` opens
  the bump. Besides the version pins (`ENGINE_REF` and the wheel URL in `pyproject.toml`, the sha256 in `uv.lock`),
  unlike the last three releases the rule pins move:
  - `tests/unit/test_engine.py`: `EXPECTED_RULES_VERSION` becomes `2026.11.1`, and `REGISTRY_DIGEST` becomes
    `715d1fddb5359262da368da57518a4c51ddb6057aeb86029ebadb1b1aaaffed1`. That value was computed upstream with this
    repository's own formula (`id|version|severity|applies_to`, in id order) on the App branch; the same formula on
    the App's current `main` gives today's pin `dd1d1f26…4c4add`. Check it against the released wheel; do not copy it
    blindly.
  - `docs/rules/catalog.md` (`make rules-doc`): the version column of the `AZ-NET-009` and `AZ-NET-019` rows goes from
    `1` to `2`, and the provenance line names `0.1.5`. The catalog does not print the framework notes, so no other line
    is expected to move.
  - `GET /api/rules` and the `rules.json` in each bundle carry the reworded notes (they serialise every framework
    mapping). Nothing in this repository is known to pin those notes; the suite will say if something does.

### 2026-11-08: engine 0.1.4 adopted; a resource name with a hedge word no longer stops the upload

- **Released.** `engine-v0.1.4` was published on 2026-11-08
  ([release](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.4)) from `1db870d`.
  `core-update.yml` opened [pull request 93](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/93).
- **What actually shipped, which is narrower than the entry below expected.** That entry was written while
  [HCW-NetworkEyes_App#361](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/361) was open and says every
  string from the export is masked. The release went further in the safe direction
  ([HCW-NetworkEyes_App#363](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/363)): a hedge word is excused
  only when it sits inside a customer *identifier* (a resource name, id or location) that has no spaces and joins the
  hedge word to a letter or digit with `-`, `.`, `/` or `:`. A resource named just `may`, a description or a tag value
  excuses nothing. Anything that still fails is withheld into `unknowns[]` with `HEDGED_WORDING_REASON`.
- **What this repository changed.**
  - `src/network_assessment/engine.py` re-exports `HEDGED_WORDING_REASON`, so lab code and tests read it from the one
    place that reaches the wheel.
  - `test_evaluation_refuses_a_finding_whose_fact_hedges` became `test_evaluation_never_reports_a_finding_whose_fact_hedges`:
    with every finding's fact made to hedge, no finding is reported and exactly the rules that had findings are in
    `unknowns[]` with that reason. The "never weaken" line in `CLAUDE.md` still holds: a hedged finding is still never
    shown; it no longer fails the whole upload.
  - New `test_samples_have_no_finding_withheld_for_hedged_wording` (one per sample), so a hedge word in the engine's own
    wording fails this repository's CI instead of turning quietly into an unknown.
  - New `test_a_resource_name_with_a_hedge_word_does_not_stop_the_upload` in `tests/unit/test_api.py`: the JSON sample
    with every `hcw-sample-` name renamed to `hcw-sample-may-` answers 201 with the same findings and unknowns counts.
    Run against `0.1.3` it fails with the old `ObservedStateViolation`, so it tests the fix, not just the new code.
- **Not changed.** `RULES_VERSION` `2026.11.0`, the registry digest, `TOPOLOGY_MODEL_VERSION` `1.5.0` (its
  `MODEL_VERSIONS` row was added ahead of time) and the rule catalog apart from its provenance line.

### 2026-11-08: engine 0.1.4 is prepared upstream: a resource name no longer stops the report

- **The problem it fixes.** The engine refuses "hedge words" (words such as "may", "could" and "should" that guess
  instead of stating what was seen) in a finding's text. In `0.1.3` that check read the whole text, including the
  customer's own resource names the rules quote, and the error it raised was not caught. So an export with one
  resource called, for example, `may-promo-listener` stopped the whole assessment, not just that finding. Nothing in
  `routes/assessments.py` catches `ObservedStateViolation`, so here the upload fails with a server error (read from
  the code, not reproduced against the running lab). Reported as
  [HCW-NetworkEyes_App#356](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/356).
- **What changes upstream.** [HCW-NetworkEyes_App#361](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/361)
  (open when this entry was written)
  makes two changes and moves the package version to `0.1.4`:
  1. The check judges only the engine's wording. Before it scans a fact, title or description, every value that came
     from the uploaded export (names, ids, locations: every string in the topology) is masked, whole words only. A
     value that is nothing but a hedge word (a resource named just `may`) is never masked.
  2. A finding that still fails the check is **withheld**, never reported: its rule goes to `unknowns[]` with the fixed
     reason `HEDGED_WORDING_REASON` (exported from `network_assessment_azure_engine.rules`; it carries no resource
     name), and the rest of the report renders.
  No rule's output changes: `RULES_VERSION` stays `2026.11.0`, the registry digest and `TOPOLOGY_MODEL_VERSION`
  (`1.5.0`) stay.
- **What this repository did meanwhile.** `tests/conftest.py` knows `network-assessment-azure-engine 0.1.4`
  (model `1.5.0`) in `MODEL_VERSIONS`; the row is unused until the bump.
- **What the bump to 0.1.4 needs.** Once the owner pushes the `engine-v0.1.4` tag on the App, `core-update.yml` opens
  the bump. Besides the version pins (`ENGINE_REF` and the wheel URL in `pyproject.toml`, the sha256 in `uv.lock`):
  - `test_evaluation_refuses_a_finding_whose_fact_hedges` in `tests/unit/test_engine.py` expects `assess()` to raise
    `ObservedStateViolation`. With `0.1.4` it no longer raises. Rewrite it to keep the same guarantee (a hedged
    finding is never reported): `a.findings` is empty for the patched rules, and every rule that had a finding is in
    `a.unknowns` with the reason `HEDGED_WORDING_REASON`. This keeps the CLAUDE.md "never weaken" line, because the
    gate still stops every hedged finding; it now stops it without failing the whole upload.
  - Add a test that the samples produce no `unknowns[]` entry with `HEDGED_WORDING_REASON`, so a hedge word in the
    engine's own wording still fails this repository's CI instead of quietly turning into an unknown.
  - Optional, worth doing: an upload test with a resource named `may-promo-listener` that answers 201 with findings.
  - `docs/rules/catalog.md`, `RULES_VERSION` and the digest pin are not expected to move (check them, do not assume).

### 2026-11-08: engine 0.1.3 adopted; the wheel now carries its own licence files

- **Released.** `engine-v0.1.3` was published on 2026-11-08 ([release](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.3)).
  The downloaded wheel's sha256 is `89a6bc2b…570ce345`, as the release page and `uv.lock` say, and its
  `.dist-info/licenses/` holds `LICENSE` and `NOTICE`.
- **Adopted** by `core-update.yml`'s bump, [pull request 91](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/91):
  the `ENGINE_REF` line and wheel URL, the sha256 in `uv.lock`, and the one row `tests/conftest.py` needs for each
  release (`MODEL_VERSIONS`, model `1.5.0`). `RULES_VERSION`, the registry digest and the catalog did not move.
- **The bundled copies match.** `tests/security/test_image_licences.py` now compares
  `third_party/network-assessment-azure-engine/{LICENSE,NOTICE}` with the wheel's, and they are byte-identical, so the
  image carries the released texts. The bundled copies stay (the label check reads them).

### 2026-11-08: engine 0.1.3 is prepared upstream (not released yet): the wheel carries its licence files

- **What changed upstream.** [HCW-NetworkEyes_App#360](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/360)
  (open when this entry was written) makes the engine wheel ship `LICENSE` (Apache-2.0) and `NOTICE` under its
  `.dist-info/licenses/` folder, with a `License-File:` line for each in its `METADATA`, and moves the package version
  to `0.1.3`. The released `engine-v0.1.2` wheel declares `License-Expression: Apache-2.0` but carries neither file.
  No rule, model or behaviour changes: `RULES_VERSION` stays `2026.11.0` and `TOPOLOGY_MODEL_VERSION` stays `1.5.0`.
- **What this repository did meanwhile.** It does not wait for the release: the image label is now
  `MIT AND Apache-2.0`, and the engine's licence text and NOTICE are bundled from `third_party/network-assessment-azure-engine/`
  into `/usr/share/licenses/network-assessment-azure-engine/` in the image (see `NOTICE` and `CHANGELOG.md`).
- **What the bump to 0.1.3 needs.** Once the owner pushes the `engine-v0.1.3` tag on the App, `core-update.yml` opens the
  bump. Expected to need only the version pins: `ENGINE_REF` and the wheel URL in `pyproject.toml`, the sha256 in
  `uv.lock`; the registry digest, `RULES_VERSION` and `MODEL_VERSIONS` should not move (check them, do not assume).
  Keep `third_party/network-assessment-azure-engine/` after the bump; it costs two small files and the label check
  still reads it. If the App changes the package `NOTICE` before releasing, copy the released one over the bundled
  copy in the same bump.

### 2026-11-08: the interim port is deleted; the wheel is the only engine

- **What changed here.** Not an upstream change: this repository finished the plan it recorded when it first ported
  the engine. With the wheel adopted at `0.1.1` and `0.1.2` and green, one pull request deleted the ported copy
  (`src/network_assessment/{model,rules,classify}`), its tests (`tests/unit/test_registry.py`, `test_enforcer.py`,
  `test_classifier.py`, `tests/unit/rules/`, `model_fixtures.py`), the lab's own normalizer
  (`src/network_assessment/ingestion/normalize.py`) and `PROVENANCE.md`. ADR-0006 records it and supersedes the
  interim part of ADR-0001.
- **What it means for the next bump.** `engine.py` no longer has a fallback: it imports the wheel or stops with
  `EngineNotInstalled`, so `ENGINE_REF none` is no longer a valid state, and `GET /api/health` / `GET /api/rules`
  never report `interim-port` again. A bump still moves the pins in `tests/unit/test_engine.py` (registry digest,
  `RULES_VERSION`), `tests/conftest.py` (`MODEL_VERSIONS`), the sample expectations and the e2e suite when the
  engine's rules change; `docs/rules/catalog.md` is regenerated by the bump job as before (unchanged by this removal).
- **What was lost, on purpose.** The test that compared the wheel's normalizer with the lab's own went with the lab's
  normalizer. `tests/unit/test_normalize.py` still pins the normalised result of the samples, against the wheel.
- **What the lab still owns.** Its list of hedge words and the hedge-free check on every rule text
  (`tests/unit/test_engine.py`, `engine.assert_text_is_hedge_free`, `scripts/rules-doc.py`); the wheel validates every
  finding at evaluation.

### 2026-11-07: engine 0.1.2 is prepared upstream (not released yet): WAF policies per listener and path rule

- **What is changing.** The App's [issue 352](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/352)
  (follow-up from the review of 0.1.1) teaches the engine the WAF policies Azure lets you link to a single
  listener (`httpListeners[].properties.firewallPolicy`) or a single path rule
  (`urlPathMaps[].properties.pathRules[].properties.firewallPolicy`); such a policy overrides the gateway-wide one
  for that listener or path. Before, a gateway with an Enabled policy and a listener linked to a Disabled policy was
  reported as protected. The App's pull request for it changes: model `TOPOLOGY_MODEL_VERSION` `1.4.0` → `1.5.0`
  (`ApplicationGateway.waf_scopes`, defaulting to empty); AZ-NET-007 v2 → **v3** and AZ-NET-025 v1 → **v2**, each
  keeping its gateway-wide finding and adding one finding per listener or path rule whose own policy is Disabled
  (007) or Enabled in Detection mode (025), keyed on that listener's or path rule's id and citing
  `waf_policies[id=...].state` / `.mode`. The gateway-wide finding is not unconditional: a listener or path rule
  linked to the gateway's own policy adds no second finding, and when every listener has its own policy
  (`ApplicationGateway.listener_count`, `gateway_policy_unused`) the gateway-wide setting applies to no traffic and
  gets no finding. `RULES_VERSION` `2026.10.0` → **`2026.11.0`**; package `0.1.2`. Rule ids, severities and
  `applies_to` do not change.
- **Done here now.** `tests/conftest.py`'s `MODEL_VERSIONS` gains `"network-assessment-azure-engine 0.1.2": "1.5.0"`.
  It is harmless against the 0.1.1 wheel this repository runs, and without it the bump would also fail
  `test_the_engine_is_one_this_edition_knows`.
- **What the bump pull request will need (not doable before the release).** `core-update.yml` opens it after the
  owner tags `engine-v0.1.2`. Its tests will fail on the version pins, which is the designed "needs adaptation"
  signal; one commit on the bump branch fixes them:
  - `tests/unit/test_engine.py`: `EXPECTED_RULES_VERSION = "2026.11.0"` and `REGISTRY_DIGEST =
    "dd1d1f26a4e80db1fb786ea4bd71374a449522e4fb13999855477d8a994c4add"` (the same `id|version|severity|applies_to`
    formula, computed from the App's branch on 2026-11-07; recompute from the wheel to confirm).
  - `2026.10.0` → `2026.11.0` in `tests/unit/test_api.py` (three places), `tests/unit/test_report.py` (two),
    `tests/unit/test_sample_expectations.py` and `tests/e2e/lab.spec.ts`; `docs/rules/catalog.md` is regenerated by
    the bump itself (`make rules-doc`).
  - `tests/unit/test_registry.py` pins the interim **port** (`network_assessment.rules`), not the wheel, so it does
    not move.
  - The pinned sample is not affected: neither gateway in `samples/sample-resource-graph.json` has a listener or
    path rule linked to its own policy, so the finding counts stay as pinned.
- **Action.** None for the owner until the App's pull request merges; then tag `engine-v0.1.2` in the App (its
  `320-release-engine.yml` publishes the wheel), and the session that handles the bump applies the list above.

### 2026-11-05: `engine-v0.1.1`, the release that fixes the five differences

- **What happened.** The App closed [issue 350](https://github.com/saulpatinojr/HCW-NetworkEyes_App/issues/350) with
  [pull request 351](https://github.com/saulpatinojr/HCW-NetworkEyes_App/pull/351) (merged as commit `39a219c`) and
  tagged it `engine-v0.1.1` ([release](https://github.com/saulpatinojr/HCW-NetworkEyes_App/releases/tag/engine-v0.1.1)).
  The wheel is published under the new name: distribution `network-assessment-azure-engine`, file
  `network_assessment_azure_engine-0.1.1-py3-none-any.whl`, import name `network_assessment_azure_engine` (the first
  name in `engine.py`'s `WHEEL_PACKAGES`).
- **What changed in the engine, against the 2026-10-31 list.** (1) AZ-NET-007 and AZ-NET-025 read the WAF policy
  linked to the gateway (`ApplicationGateway.effective_waf_enabled` / `effective_waf_mode`); on the sample the
  summary is 11 high / 19 medium, as pinned. (2) Every rule has a description and a remediation. (3) No rule text
  or finding carries a hedge word (AZ-COST-002's remediation and AZ-NET-031's recommendation reworded). (4)
  Evidence references are `export:<subscription>.<path>` for a normalised export (`discovery:` for the App's live
  runs; the prefix follows the topology's `source`). (5) AZ-NET-004's fact no longer prints `NoneMbps`. Not changed:
  AZ-NET-031 still keys its finding on the private-link connection id, and the live-only `unknowns[]` reasons are
  still field paths; neither is gated here. Rule ids, versions, severities, `RULES_VERSION` (`2026.10.0`) and the
  registry digest are unchanged, so `tests/unit/test_registry.py` and `test_engine.py` keep their pins.
- **Proof before the release.** The App built the 0.1.1 wheel locally and ran this repository's checks on a scratch
  copy of the `core-update/engine-v0.1.0` branch with the wheel installed in place of 0.1.0: `uv run pytest -q`
  went from 41 failed / 470 passed to 511 passed; `scripts/rules-doc.py --check` from refused (`expected` in
  AZ-COST-002) to in sync (422 lines); `ruff check .` passed both times. Without the row below, exactly one test
  failed, `test_the_engine_is_one_this_edition_knows`: the "new engine" signal working as designed.
- **Reaches this repository? Yes, one line.** `tests/conftest.py`'s `MODEL_VERSIONS` table gains
  `"network-assessment-azure-engine 0.1.1": "1.4.0"` (the wheel's `TOPOLOGY_MODEL_VERSION` is still `1.4.0`), so the
  bump pull request that `core-update.yml` opens for 0.1.1 passes `test`, `rules-doc` and `pip-audit` on its own
  and auto-merge lands it. No engine, pin or lab code change here; the bump does the pin and regenerates
  `docs/rules/catalog.md`.
- **Action.** None for the owner. The next scheduled `core-update.yml` run (every six hours, `41 */6 * * *` UTC)
  opens the 0.1.1 bump; close [pull request 74](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/74)
  (the 0.1.0 bump) when it does. After that bump merges, the interim port under `src/network_assessment/{model,
  rules,classify}` is deleted as `PROVENANCE.md` plans.

### 2026-11-05: the first real bump pull request opened, and two workflow defects it showed

- **What happened.** The scheduled `core-update.yml` run of 04:39 UTC ([run 41969178172](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/41969178172)) did what the
  2026-10-31 entry said it would: it pinned `cna-azure-network-engine` 0.1.0 by URL, re-locked, and opened
  [pull request 74](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/74) with the HCW Main Admin App, with auto-merge turned on. The pull request's own checks started
  by themselves ([ci](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/41969287315), [security](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/runs/41969287470)): `lint`, `image`, `e2e`, `secret-scan`, `dependency-review` and
  CodeQL passed; `test` (41 failures), `rules-doc` and `pip-audit` failed. This is the first bump pull request for this
  edition, and it is the proof asked for on [MigrateOrchestrator issue 50](https://github.com/saulpatinojr/HCW-MigrateOrchestrator_AddOn/issues/50).
- **The engine is as the 2026-10-31 entry described it.** The 41 test failures and the catalog refusal are the five
  differences already listed there, seen on the real wheel: 33 rules with an empty `description` and 34 with an empty
  `remediation` (`test_every_rule_text_is_present_and_hedge_free`), `expected` in AZ-COST-002's remediation
  (`rules-doc.py --check` and `test_report_facts_are_hedge_free`), `discovery:` evidence references
  (`test_findings_cite_the_export_and_state_facts_only`), and AZ-NET-007 firing twice while AZ-NET-025 never fires
  (`test_every_portable_rule_fires_and_counts_are_pinned`, `test_summary_is_pinned`). None of them is patched here;
  they wait for the App's next engine release. The pull request stays open and unmerged until then.
- **Defect 1, fixed here: the bump said "compatible".** The pull request was titled and labelled `compatible` although
  the catalog check had refused the wheel. The compatibility step ran its checks as one `ruff && rules-doc --check &&
  pytest` line under `set -e`, and bash does not stop at a failure inside such a list (only the last member counts), so
  the refused catalog fell through to the browser suite, which passed, and the step reported success; `pytest` never
  ran in that job. Each check is now its own line, and `tests/security/test_core_update_app_token.py` runs the step
  with stubbed tools that fail one check at a time. The same shape is in Cloud Assessor's and Cloud Crawler's
  `core-update.yml` (reported, not changed here).
- **Defect 2, fixed here: `pip-audit` cannot audit the engine.** The wheel is a GitHub Release asset, not a PyPI
  package, so `pip-audit --strict` failed with `Dependency not found on PyPI and could not be audited:
  cna-azure-network-engine (0.1.0)`. The export the job audits now leaves out the two engine distribution names
  (`--no-emit-package`, as Cloud Assessor's and Cloud Crawler's `security.yml` already do for their engines); the
  engine's own dependencies stay in the export and are still audited, `--strict` stays, and the image's export keeps
  the engine. On the bump's lock the audited set is the same fourteen packages as on `main`, with no known
  vulnerabilities. `tests/security/test_security_workflow.py` pins both exports.
- **Reaches this repository?** Yes: the two workflows and their tests. No engine, pin or lab code changes. The
  `compatible` label on pull request 74 was replaced by `needs-adaptation` by hand; the next scheduled run rewrites
  the title with the corrected report.
- **Action.** Ask the App for the release (the row in "Open upstream decisions" below). When it is tagged,
  `core-update.yml` opens a new bump pull request for it; close pull request 74 then.

### 2026-11-05: the HCW Main Admin App is also used by two App repositories (credential notes only)

- On 2026-11-04 the lockfile workflow in two other App repositories, `HCW-CloudCrawler_App` and `HCW-CloudAssessor_App` (not this edition's
  upstream) were changed to push Dependabot's regenerated
  lockfile exports with the HCW Main Admin GitHub App, the App this repository's `core-update.yml` uses ([HCW-CloudCrawler_App#71](https://github.com/saulpatinojr/HCW-CloudCrawler_App/pull/71), [HCW-CloudAssessor_App#87](https://github.com/saulpatinojr/HCW-CloudAssessor_App/pull/87); owner decision on [HCW-CloudCrawler_App#70](https://github.com/saulpatinojr/HCW-CloudCrawler_App/issues/70)). Once the owner installs it there, the App is on six repositories, not four.
- **Reaches this edition? Only the notes.** No engine, pin, workflow behaviour or test changes here. Those two
  repositories hold a separate private key as Dependabot secrets, so rotating this repository's key is unchanged. The
  `core-update.yml` comment and `VALIDATION.md` now say where the App is installed, and the accepted-risk note says a
  stolen key could reach those two repositories as well, whose `main` still needs an approved pull request.

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
| A release that fixes the five differences of 2026-10-31 (entry above) | **Not tracked in the App yet.** An issue text for the App was written on 2026-11-05 (it lists the five items with the failing test names from [pull request 74](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pull/74)); opening it there is the owner's step, recorded on [MigrateOrchestrator issue 50](https://github.com/saulpatinojr/HCW-MigrateOrchestrator_AddOn/issues/50) | Until it exists, the bump for `0.1.0` stays open with failing `test` and `rules-doc` checks and nothing merges: auto-merge is turned on (`CORE_AUTOMERGE` is `true`), but it waits for the required checks. |
| Next engine release (a new version) | App `REFACTOR_APP.md` section 15, steps 3 and later | Change set B brings `RULES_VERSION` bumps and web findings ids; each arrives here as a `core-update.yml` pull request. |
| Docker Hub sign-in for the App's own image builds | App `REVIEW.md` R-013 | Concerns the App's images, not this repository's image. |
