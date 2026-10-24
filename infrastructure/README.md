# Infrastructure

| Path | What |
|---|---|
| `docker/Dockerfile` | The lab image (`docker.io/hybridcloudworks/hcw-networkeyes`): two stages on one digest-pinned base, hash-pinned dependencies, no pip at runtime, uid 10001, `HEALTHCHECK`, `CMD python -m network_assessment`. `ARG EDITION=lab` is asserted in both stages. |
| `docker/versions.env` | `BASE_IMAGE`, `BASE_DIGEST`, `BASE_PYTHON_VERSION`; CI fails when any `FROM` differs from `BASE_IMAGE@BASE_DIGEST`. |
| `coder/template/main.tf` | Guided workspace template (`na-guided-lab`) on `docker.io/hybridcloudworks/hcw-lab:latest`: pulls the assessment `bundle.zip` once via `x-bundle-token` and opens `code-server` (ADR-0005). |
| `../docker-compose.yml` | Local development only, hardened like the lab host's `docker_container` (read-only root, tmpfs `/tmp`, `cap_drop ALL`, `no-new-privileges`, 512m, 256 pids, one CPU, bridge network, no mounts). |

There is no host or cloud Terraform here and there must not be (AddOn Integration Standard, section 3): the lab host belongs to the
website repository (`lab-host/ansible`, role `addons`), and the Azure appliance belongs to the Core
(`saulpatinojr/HCW-NetworkEyes_App`, its `REFACTOR_APP.md` change set G). Only the per-assessment Coder workspace template (`coder/template/main.tf`) lives here.

The lab application (with the ported engine under `network_assessment/{model,rules,classify}`, ADR-0001) is copied
into `/usr/local/lib/python3.14/site-packages` as a source tree rather than built as a wheel, so no build backend
enters the image. The build stage exports `uv.lock` with `uv export --frozen --format requirements-txt --no-dev
--no-emit-project --no-emit-workspace --no-header` (hashes on by default), using the uv CI uses by digest; that
export is the only input `pip install --require-hashes --no-deps` reads, and uv stays in the build stage. There is no
committed export: `uv.lock` is the one lock, which Dependabot (`uv` ecosystem) updates with `pyproject.toml`. The App (`HCW-NetworkEyes_App`) has published `cna-azure-network-engine` as `engine-v0.1.0` (2026-10-12); once it is adopted (`docs/whats-new-upstream.md`), the wheel (a GitHub Release asset, pinned by URL and sha256) joins `uv.lock` and the ported tree is deleted.

Image build, Trivy and the `import azure` image check run in CI (`publish-images.yml`); the authoring container had no
Docker daemon (see `VALIDATION.md`).
