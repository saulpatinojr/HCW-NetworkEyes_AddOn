# Operations runbook (lab edition)

The container is run by the website repository's `addons` role on the lab host (`docs/deployment/lab-host.md`). The
commands below are bash on the host unless stated. Nothing here touches a cloud.

| Task | How | What success looks like |
|---|---|---|
| Health | `curl -s http://127.0.0.1:18082/api/health` | `{"ok":true,"id":"network-assessment","version":"0.1.3","edition":"lab",…,"azureConnectivity":"disabled-by-design","rules":{"version":"2026.11.1","count":45,"liveOnly":11},"model":{"version":"1.5.0"},…}` within a second |
| Which version is live | `curl -sI http://127.0.0.1:18082/api/health \| grep -i x-addon-version` | `x-addon-version: 0.1.3` |
| Logs | `docker logs --since 1h hcw-addon-network-assessment` | JSON lines on stderr: `startup` (rule count), `assessment_created` (rows, resources, findings, unknowns, warnings, duration), `assessment_read`, `assessment_rejected` (a code), `assessment_deleted`, `rate_limited`, `overloaded`, `turnstile_rejected` (a count of codes), `sweep`, `shutdown`. Never ids, names, tokens, file names, prefixes or cell content. |
| Restart | `docker restart hcw-addon-network-assessment` | Health answers again within the `HEALTHCHECK` start period (10 s). Every in-memory assessment is gone by design. |
| Upgrade / rollback | Move `image_tag` and `image_digest` in the website's `group_vars/all.yml`; run `bootstrap.sh` | The role pulls by digest, recreates the container and waits for health. Rollback is the previous digest. |
| Stop serving (kill switch) | Website: unset `ADDON_NETWORK_ASSESSMENT_URL` (the proxy answers `configured:false`, the page shows the one sentence). Host: `enabled: false` on the row and run `bootstrap.sh` (the container is removed; Caddy answers 503 with the same sentence). | Visitors see `This tool isn't available right now.` and nothing else |
| Abuse | Per client address: `NA_RATE_LIMIT_POSTS` per `NA_RATE_LIMIT_WINDOW_MINUTES` (defaults 10 / 10) and `NA_MAX_CONCURRENT` (2). Tighten in `addons[].env`; human verification is already required on every upload. A burst shows as `rate_limited` and `overloaded` log lines. | 429 / 503 answers with `Retry-After`; health stays 200 |
| Verification outage | Uploads answer `403 turnstile_failed` with code `verification-unavailable` (the siteverify call failed within 5 s). Nothing to do on the host; the pane tells the visitor to retry. | Health unaffected |
| Rotate the verification secret | `hcw-vault-set vault_addon_network_assessment_turnstile_secret` on the host checkout, then `bootstrap.sh` (the role recreates the container with the new value) | Health 200; an upload with a fresh token answers 201 |
| Data request | There is nothing to retrieve or erase: assessments live in process memory for at most `NA_TTL_MINUTES` (120), are returned only to the holder of the owner token, and a restart purges everything. State this in the reply. | — |
| Memory or pids pressure | The role caps the container at 512m and 256 pids; the store holds at most `NA_MAX_ITEMS` (200) assessments (oldest evicted) of at most 5 MB input each. | `docker stats hcw-addon-network-assessment` stays under the caps |

Troubleshooting a container that will not start: `docker logs hcw-addon-network-assessment` prints one line
`{"event":"startup_refused","reason":"…"}` (exit code 3) when the edition guard refused (an identity endpoint or a
credential variable in the environment) or a setting is out of range (`NA_*` numeric settings are integers between
their minimum and 1,000,000,000). Neither is fixed on the host beyond removing the offending environment.

## Keeping the base image on the website's pin (`base-update`)

The lab image is built on a base image (the image a build starts from). The website decides which one, in its file
`lab-image/versions.env`. This repository keeps a copy of that choice in `infrastructure/docker/versions.env` and repeats
it on every `FROM` line (the line that names the starting image) of `infrastructure/docker/Dockerfile`. Once a day, at
07:37 UTC, the workflow [`base-update`](../../.github/workflows/base-update.yml) compares the two. When the website has
moved, it opens one pull request that changes `versions.env` and every `FROM` together. A person reviews and merges that
pull request; nothing is merged for you. On a normal day nothing happens: the run is green and prints `changed=false`.
Runs: <https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/actions/workflows/base-update.yml>. Open pull requests it
made: <https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pulls?q=is%3Apr+is%3Aopen+head%3Abase-update%2Fwebsite-base>.
Until the proof at the end of this section has been run once and recorded in `VALIDATION.md`, this section describes what
the workflow is built to do, not what has been seen happening.

**When the pull request appears.** Wait for its checks (the `image` check builds the image on the new base), then merge it.
Success looks like this: the next run of the `base-follows-website` job in `security.yml` on `main` is green.

**If you need to change the pull request.** A commit you push to the branch `base-update/website-base` is kept: while the
branch already holds the website's pin, the daily run leaves the pull request alone. If the website moves again, the branch
is rebuilt from `main` and your commit is replaced. For a change that has to last, close the pull request and make the
change on your own branch. If the website moves back (or someone moves `main` to the website's pin by hand) while a pull
request is open, the next run closes it as no longer needed.

**When the run is red.** Open the failed step's log and look for a line that starts with `::error::`. The refusals in
the table below print one; a network failure while the website's file is being read may print only the tool's own message,
so read the log even when there is no such line. Do not rely on the weekly
`base-follows-website` job to show it: that job compares only the image and its digest (`BASE_IMAGE` and `BASE_DIGEST`), not
the Python version. It usually goes red as well when the website moves, but if the website changes only
`BASE_PYTHON_VERSION` to another minor line (for example 3.15 to 3.16), `base-update` refuses and goes red while the weekly
job stays green. So watch for failed `base-update` runs on their own (GitHub can notify the person who last changed the
workflow's `cron` line, as their notification settings allow, so do not count on an email; the Actions tab lists every run). What the run left behind depends on where it stopped:

- If the red step is in the first job, `plan`, or is the step called "Apply the move" in the second, nothing was pushed and
  no pull request was opened: those steps only read and edit files on the runner.
- If the red step is a later step of the second job (the token, the commit identity or "Open the pull request"), the branch
  `base-update/website-base` may already have been pushed without its pull request. Look before you act. Success: the first
  command lists the pull requests of that branch (open or closed; nothing is fine), and the second prints
  `refs/heads/base-update/website-base` when the branch exists. A branch without a pull request does no harm: the next
  successful run reuses it and opens the pull request.

  ```powershell
  gh pr list -R saulpatinojr/HCW-NetworkEyes_AddOn --head base-update/website-base --state all
  ```

  ```powershell
  gh api "repos/saulpatinojr/HCW-NetworkEyes_AddOn/git/matching-refs/heads/base-update/website-base" --jq ".[].ref"
  ```

| The `::error::` line says | What it means | What to do |
|---|---|---|
| `the website's base image is X, not Y` | The website switched to a different image repository. | A decision for a person: change `versions.env` and the `FROM` lines by hand if the new image is wanted here. |
| `the website moved Python from 3.15 to 3.16` | The website moved to a new Python minor line. The Dockerfile, `pyproject.toml` and `ci.yml` name the line (`python3.15`, `requires-python`, `PYTHON_VERSION`). | A decision for a person: adopt the new line by hand in one pull request, or wait. |
| `Dockerfile line N: FROM ... is neither an earlier stage nor ...` or `still carries` | The Dockerfile has a `FROM` (or another line) the script cannot move. | Fix the Dockerfile so every `FROM` that is not an earlier stage is exactly `BASE_IMAGE@BASE_DIGEST`, or move the pin by hand. |
| `expected exactly one BASE_... line`, `is not an image reference` or `is not sha256:` | A `versions.env` (the website's or this one) is malformed or repeats a key. | Read the file named in the message. If it is the website's file, tell the website's owner; do not edit this repository to match it. |
| `the registry did not show ...` | The digest does not exist, or Docker Hub did not answer. | Run it again later: `gh workflow run base-update.yml --ref main`. If it keeps failing, the website's digest is wrong: tell the website's owner. |
| `... lacks platforms that ... has` | The website's new digest dropped a platform the old one had (for example `linux/arm64`). | A decision for a person; do not merge anything until it is settled. |

**If the daily run goes quiet.** GitHub switches off scheduled workflows in a public repository after 60 days without
repository activity (a push, a merged pull request and the like count as activity). That would switch off `base-update` and
the weekly `base-follows-website` job in `security.yml` together, so in that one case the weekly job is not an independent
second check. To look, list the workflows and their state. Success: every row says `active`; a workflow GitHub has switched
off says `disabled_inactivity`. To switch the two back on, run the second command (it does no harm to a workflow that is
already on); success is that it prints a line saying the workflow was enabled.

```powershell
gh workflow list -R saulpatinojr/HCW-NetworkEyes_AddOn --all --json name,state,path | ConvertFrom-Json | Where-Object { $_.path -like ".github/workflows/*" } | Select-Object state, path | Format-Table -AutoSize
```

```powershell
gh workflow enable base-update.yml -R saulpatinojr/HCW-NetworkEyes_AddOn; gh workflow enable security.yml -R saulpatinojr/HCW-NetworkEyes_AddOn
```

**Proving it (run this once after the workflow first reaches `main`, and again after any change to `base-update.yml`).** It
uses a throwaway branch, so `main` is never touched. The commands are PowerShell. The previous digest used below is the one
this repository pinned before 2026-10-26 (`git log -p -- infrastructure/docker/versions.env`); it is still in the registry.

**Read this before you start.** The workflow's pull request asks the repository owner for a review (`CODEOWNERS` names the
owner for every path), so a proof pull request looks exactly like a real one and is easy to merge by mistake. It happened
twice in the first proof of this workflow, which ran in the Cloud Assessor add-on (on 2026-10-27): the owner's account merged
the proof's pull request into the throwaway branch about ten minutes after it opened, which is about when its checks finish,
and the step that needed it could no longer be done.
Nothing on `main` was affected, because the proof's pull requests go into the throwaway branch. To avoid it, do steps 5 to
11 in one sitting without pausing (they take about two minutes of waiting), and do not wait for the checks in step 8. If a
push in step 11 is refused because the proof's pull request was merged, reset the throwaway folder and begin again at
step 3: `git -C $wt fetch origin; git -C $wt reset --hard origin/proof/base-update`. Step 10 can be left out of a repeat.

1. Use one PowerShell window for every step (later steps use the variables set here). Set the names and a helper that starts
   the workflow on the throwaway branch and waits for the new run. Success: no output.

   ```powershell
   $repo = "saulpatinojr/HCW-NetworkEyes_AddOn"; $clone = "C:\Users\saulp\Workspace\HCW-NetworkEyes_AddOn"; $wt = "C:\Users\saulp\Workspace\HCW-wt-neproof"
   ```

   ```powershell
   function Start-BaseUpdate { $before = gh run list -R $repo --workflow base-update.yml --branch proof/base-update --limit 1 --json databaseId --jq ".[0].databaseId"; gh workflow run base-update.yml -R $repo --ref proof/base-update; if ($LASTEXITCODE -ne 0) { Write-Host "the workflow could not be started (is base-update.yml on main yet?)"; return }; $global:run = $null; for ($i = 0; $i -lt 40 -and (-not $global:run -or $global:run -eq $before); $i++) { Start-Sleep -Seconds 3; $global:run = gh run list -R $repo --workflow base-update.yml --branch proof/base-update --limit 1 --json databaseId --jq ".[0].databaseId" }; if (-not $global:run -or $global:run -eq $before) { Write-Host "no new run appeared within two minutes"; return }; gh run watch $global:run -R $repo --exit-status }
   ```

2. First make sure the proof cannot meet a real update. It reuses the branch `base-update/website-base`, which a real update
   (the website's pin differing from `main`'s) uses too, and step 11 puts the throwaway branch back to what `main` holds.
   So the proof is only safe when `main` already has the website's pin. In that case the daily run at 07:37 UTC changes
   nothing while the proof is going on (it also looks only at pull requests into `main`, and the proof's pull requests go
   into the throwaway branch). Two checks. Success: the first command prints `same: the website and main hold the same pin`
   and `lines read: 3 and 3`; the second prints nothing (or `no pull requests match`).
   If the first says `DIFFERENT`, stop: a real update is due. Let the daily run open the real pull request (or start it with
   `gh workflow run base-update.yml --ref main`), merge it, and begin again. If the second lists a pull request, stop: it
   is a real one.

   ```powershell
   $a = gh api "repos/saulpatinojr/HCW-HybridCloudWorks/contents/lab-image/versions.env" -H "Accept: application/vnd.github.raw+json" | Where-Object { $_ -match "^BASE_" }; $b = gh api "repos/$repo/contents/infrastructure/docker/versions.env?ref=main" -H "Accept: application/vnd.github.raw+json" | Where-Object { $_ -match "^BASE_" }; if (-not $a -or ($a -join "|") -ne ($b -join "|")) { "DIFFERENT: stop and read the note under this step" } else { "same: the website and main hold the same pin" }; "lines read: $(@($a).Count) and $(@($b).Count)"
   ```

   ```powershell
   gh pr list -R $repo --head base-update/website-base --state open
   ```

   Then make a throwaway branch in its own folder. Success: the command prints `HEAD is now at` and a commit of `main`.

   ```powershell
   git -C $clone fetch origin; git -C $clone worktree add $wt -b proof/base-update origin/main
   ```

3. Put the pin one release back, in `versions.env` and both `FROM` lines. Success: the second line shows 2 files changed.

   ```powershell
   foreach ($p in "infrastructure\docker\versions.env", "infrastructure\docker\Dockerfile") { $f = (Resolve-Path -LiteralPath (Join-Path $wt $p)).Path; $t = [System.IO.File]::ReadAllText($f); [System.IO.File]::WriteAllText($f, $t.Replace("sha256:fbecd461fc72d21b2143c6eaba25143738079154a6d0ea3da3aec724f50eed4a", "sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170")) }; git -C $wt diff --stat
   ```

   If the first digest is no longer the pin in `main`'s `versions.env`, nothing changes and `git diff --stat` prints nothing: read
   the `BASE_DIGEST` line of `versions.env` and use that value in place of the first digest.

4. Commit and push it. Success: the push prints `[new branch]  proof/base-update -> proof/base-update`.

   ```powershell
   git -C $wt -c user.email=34853639+saulpatinojr@users.noreply.github.com -c user.name="Saul Patino" commit -am "proof: base image one release back"; git -C $wt push -u origin proof/base-update
   ```

5. Run the workflow on that branch and wait for it. Success: it ends with both jobs green (`plan` and `open-pr`).

   ```powershell
   Start-BaseUpdate
   ```

   If it ends red, read the `::error::` line (table above) and stop; this is the proof failing, which is what it is for.

6. Read what the plan decided. Success: the lines show `changed=true`, `old=python:` with `a2b82f3c48559aa0`, `new=python:`
   with `fbecd461fc72d21b` (or the website's newer pin), and a list of platforms that includes `linux/386` and
   `linux/s390x`. (These patterns match only what the run printed, not the script text, so they cannot match by accident.)

   ```powershell
   gh run view $run -R $repo --log | Select-String "changed=true|old=python:|new=python:|linux/386|linux/s390x"
   ```

7. Find the pull request it opened. Success: exactly one pull request; its base is `proof/base-update`; its title is
   `CI: the base image follows the website's current digest (` and 12 characters and `)`; its author is `app/hcw-main-admin`;
   and the last line shows the ticked box `- [x] The new digest is an index` (an unticked `[ ]` means the registry could not
   show the old digest, which the plan log's warning would also say).

   ```powershell
   $pr = gh pr list -R $repo --head base-update/website-base --state open --json number --jq ".[0].number"; gh pr list -R $repo --head base-update/website-base --state open --json number,url,baseRefName,title,author; gh pr view $pr -R $repo --json body --jq .body | Select-String "\[.\] The new digest is an index"
   ```

8. See that its checks started. Success: the list shows `lint`, `test`, `image`, `rules-doc`, `package`, `e2e` and others,
   pending or passing; they exist only because the pull request was opened with the App token. Do not wait for them to
   finish: that takes about ten minutes, which is when the pull request is most likely to be merged by mistake (see above).
   In the Cloud Assessor proof they all finished green. Also note whether the pull request says it needs an extra approval.

   ```powershell
   gh pr checks $pr -R $repo
   ```

9. Check the commit is credited to the App's bot user. Success: a line that names `hcw-main-admin` (GitHub may print it with
   or without `[bot]` after it).

   ```powershell
   gh pr view $pr -R $repo --json commits --jq ".commits[].authors[].login"
   ```

10. Check that a person's commit on the pull request branch survives a second run. Success: the run is green; a line shows
    `left alone` (matched on the run's own notice, not on the script text); the job list shows `open-pr: skipped`; the last
    line printed is the commit you pushed. (An empty commit proves the guard; it does not prove what happens to a changed file.)

    ```powershell
    git -C $wt fetch origin base-update/website-base; git -C $wt switch -c proof/person-fix origin/base-update/website-base; git -C $wt -c user.email=34853639+saulpatinojr@users.noreply.github.com -c user.name="Saul Patino" commit --allow-empty -m "proof: a fix a person pushed"; git -C $wt push origin HEAD:base-update/website-base; Start-BaseUpdate; gh run view $run -R $repo --log | Select-String "##\[notice\].*left alone"; (gh run view $run -R $repo --json jobs | ConvertFrom-Json).jobs | ForEach-Object { "$($_.name): $($_.conclusion)" }; git -C $wt fetch origin; git -C $wt log origin/base-update/website-base -1 --format=%s
    ```

11. Check that a pull request that has become unnecessary is closed. Move the throwaway branch to the website's pin (undoing
    the commit of step 4 does that, because step 2 checked that `main` holds the website's pin) and run again. Success: the run is green; a line shows `obsolete`; the job list shows `open-pr: success`; the last line prints
    `CLOSED`. The workflow closes it by deleting the branch `base-update/website-base`. If the last line prints `OPEN` or
    `MERGED`, the proof has found a fault: record it and do not clean up before reading the `open-pr` log.

    ```powershell
    git -C $wt switch proof/base-update; git -C $wt -c user.email=34853639+saulpatinojr@users.noreply.github.com -c user.name="Saul Patino" revert --no-edit HEAD; git -C $wt push origin proof/base-update; Start-BaseUpdate; gh run view $run -R $repo --log | Select-String "##\[notice\].*obsolete"; (gh run view $run -R $repo --json jobs | ConvertFrom-Json).jobs | ForEach-Object { "$($_.name): $($_.conclusion)" }; gh pr view $pr -R $repo --json state --jq ".state"
    ```

12. Clean up. This deletes only what the proof made: the branch `base-update/website-base` (step 11 may already have deleted it,
    and then the delete command answers that the reference does not exist, which is fine), the throwaway branch and its
    folder. First check that the branch has not become a real one since step 2 (for example because the website moved while
    you were working). Success: the first command prints nothing (or `no pull requests match`). If it lists a pull request
    into `main`, stop and do not delete the branch: it is a real pull request, and the proof must be cleaned up by hand around
    it. Success of the second command: it prints nothing (or `no pull requests match`), so no pull request is left open.

    ```powershell
    gh pr list -R $repo --head base-update/website-base --base main --state open
    ```

    ```powershell
    gh api -X DELETE "repos/$repo/git/refs/heads/base-update/website-base"; git -C $clone push origin --delete proof/base-update; git -C $clone worktree remove --force $wt; git -C $clone branch -D proof/base-update proof/person-fix; gh pr list -R $repo --head base-update/website-base --state open
    ```

Record the run links, the pull request link and what steps 7 to 11 showed in `VALIDATION.md`.

## Keeping uv away from the engine's address (the engine's static metadata)

**What this is about.** The engine (`network-assessment-azure-engine`, the rules library written in the App repository) is pinned in `pyproject.toml` by the address of its release file on
GitHub, a wheel (the Python package file, ending `.whl`). Whenever uv (the tool that installs this project's Python
packages) has to re-resolve `uv.lock` (the file that records the exact version and checksum of every package), it needs
the engine's metadata: its name, version and what it depends on. That happens on `uv lock`, on CI's `uv lock --check`,
in the engine-update workflow, and in Dependabot's uv job, once for every package Dependabot tries to update.

**What goes wrong without the fix.** uv 0.13 and later (CI uses 0.13.7) ask the wheel's address with a HEAD first (a
request for the file's headers, not the file). GitHub answers with a redirect to a short-lived signed download link on
`objects.githubusercontent.com`, and from a cloud session on 2026-11-13 that link answered the HEAD with `401` (HTTP's
"not authorised"), so `uv lock` and `uv lock --check` failed. A normal download (a GET) of the same address worked. uv
0.11.32, which CI used before, never sends that HEAD, which is why this did not show earlier. The Cloud Crawler add-on met
the same failure in its Dependabot runs on 2026-10-27, where Dependabot reported it as a "private source" problem although
nothing is private; its runbook has the full story.

**The fix.** `pyproject.toml` holds the engine's dependency list itself, in the entry `[[tool.uv.dependency-metadata]]`
([uv's description](https://docs.astral.sh/uv/concepts/resolution/)), copied from the wheel's own `METADATA` file (the
description file inside the wheel). With it, uv has nothing to ask the address: on 2026-11-13 a `uv lock` with uv 0.13.7
from an empty cache made 100 requests, all to PyPI and none to GitHub, and `uv lock --check` made none. `uv.lock` records
the entry in its `[manifest]` block. The wheel's address and its sha256 in the lock are unchanged, so the image build
still checks the engine's checksum, and the image build's `uv export` output is byte-identical.

**What you do when the engine moves.** Normally nothing. When the App publishes a new engine release, `core-update.yml`
opens a pull request ([open ones](https://github.com/saulpatinojr/HCW-NetworkEyes_AddOn/pulls?q=is%3Apr+is%3Aopen+label%3Acore-update)) and moves the pin and the entry's `version` line (the one that ends in
`# ENGINE_METADATA`) together, by replacing those two marked lines whole in both of its jobs; its pull-request job then lets only that version, and nothing else, change in the lock's `[manifest]` block. The entry's `requires-dist` list (what the engine depends on) and its `provides-extra` list (the optional extras the engine offers; today one, `azure`, which this edition never installs) is a copy, so
the test `test_static_metadata_matches_the_installed_wheel` (in `tests/security/test_engine_static_metadata.py`) compares
it with the wheel that really got installed. If the new release changed its dependencies, that test fails, the
compatibility check in the workflow run goes red and the pull request carries the label `needs-adaptation`. Then:

1. Print the new wheel's metadata. These are two PowerShell commands, run one after the other in the same window from any
   folder; the first downloads the newest `engine-v` release's wheel into a new temporary folder, the second reads it. Check that the
   `Version:` line equals the version in the pull request's title. Success: the second prints lines starting `Name:`,
   `Version:`, `Requires-Python:` and `Requires-Dist:` (one per dependency), and `Provides-Extra:` lines if the engine
   has extras.

   ```powershell
   $rel = (gh api "repos/saulpatinojr/HCW-NetworkEyes_App/releases?per_page=50" | Out-String | ConvertFrom-Json); $tag = ($rel | Where-Object { -not $_.draft -and -not $_.prerelease -and $_.tag_name -like "engine-v*" } | Select-Object -First 1).tag_name; $dir = Join-Path $env:TEMP ("engine-wheel-" + (Get-Date -Format "yyyyMMdd-HHmmss")); gh release download $tag -R saulpatinojr/HCW-NetworkEyes_App --pattern "*.whl" --dir $dir
   ```

   ```powershell
   Add-Type -AssemblyName System.IO.Compression.FileSystem; $zip = [IO.Compression.ZipFile]::OpenRead((Get-ChildItem "$dir\*.whl").FullName); $entry = $zip.Entries | Where-Object { $_.FullName -like "*.dist-info/METADATA" }; (New-Object IO.StreamReader($entry.Open())).ReadToEnd() -split "`n" | Select-String "^(Name|Version|Requires-Python|Requires-Dist|Provides-Extra):"; $zip.Dispose()
   ```

2. A dependency that was not there before is new code in the image and needs a person's decision before the pull request
   is merged: check it against the "Never weaken" rules in [`CLAUDE.md`](../../CLAUDE.md) (above all, no cloud SDK and no
   way to build a cloud credential, proved by `tests/security/test_edition_boundary.py`), its licence, and whether it is
   maintained. If it is not acceptable, do not merge; tell the owner.
3. On the pull request's branch, edit the entry `[[tool.uv.dependency-metadata]]` in `pyproject.toml` so that its
   `requires-dist` list says what step 1 printed on the `Requires-Dist:` lines (all of them, including any that end in
   `; extra == "..."`), and its `provides-extra` list names exactly the `Provides-Extra:` lines (remove the field if
   there are none). The order inside a range does not matter (`pydantic<3,>=2.14` and `pydantic>=2.14,<3` are the same).
   Leave `requires-python` out of the entry: Dependabot copies the first `requires-python` in `uv.lock` over every other
   one, so a different range there would break the lock of its pull requests. The test
   `test_wheel_accepts_every_python_the_project_allows` checks the engine's `Requires-Python` instead.
   If the release is published under the engine's other name (`cna-azure-network-engine` instead of
   `network-assessment-azure-engine`), the workflow stops at this entry and writes nothing: change the entry's `name`
   along with the pin by hand in the same pull request.
4. Switch to the pull request's branch. This PowerShell line, run in your clone of this repository, finds the
   `core-update/...` branch on GitHub (normally there is only one; if several, the last one listed) and switches to it.
   Success: git prints `Switched to branch 'core-update/...'`.

   ```powershell
   $b = (git ls-remote --heads origin 'core-update/*' | Select-Object -Last 1).Split("`t")[1].Replace('refs/heads/', ''); git fetch origin $b; git switch $b
   ```

   Then rebuild the lock with the uv version `ci.yml` names in `UV_VERSION` (0.13.7 today; use the number that file
   shows), commit `pyproject.toml` and `uv.lock`, and push. Success: it prints `Resolved` and a package count, and the
   pull request's checks go green. Do this soon after the pull request opens and merge it once green: while it is open,
   the scheduled engine-update run (every six hours) rebuilds the same branch from `main`, which is expected to replace
   a hand-made change (read from the pull-request action's documentation, not tested here).

   ```powershell
   uvx uv@0.13.7 lock
   ```
