# Network Assessment lab edition image: docker.io/hybridcloudworks/img-ne-lab-addon
#
# Two stages on one digest-pinned base (infrastructure/docker/versions.env; CI checks every FROM against it).
#   build  exports the hash-pinned third-party set from uv.lock (`uv export --frozen`, with the uv CI uses, by
#          digest; nothing resolves, and uv never reaches the lab stage), installs it into /install with
#          pip --require-hashes --no-deps (nothing resolves beyond the lock), then places the lab application
#          (the engine itself is the pinned wheel installed with the rest, ADR-0006) beside them as a source tree,
#          so no build backend enters the image.
#   lab    the runtime: Debian security updates (retries off, per-run cache bust), /install copied in, pip/ensurepip/setuptools removed, uid 10001, read-only
#          friendly (writes nothing), HEALTHCHECK on /api/health through urllib, CMD python -m network_assessment.
#
# The lab edition is technically unable to reach Azure: no cloud SDK is installed, the process refuses to start
# under an identity endpoint, and publish-images.yml asserts `python -c "import azure"` fails inside this image.
# ARG EDITION must be "lab"; the appliance edition is defined upstream (saulpatinojr/HCW-NetworkEyes_App), never here.
# The container runs on the default bridge network with no host mounts, so the lab host's Arc identity endpoint
# is unreachable from inside it (docs/security/threat-model.md).
#
# Build:  docker build -f infrastructure/docker/Dockerfile --build-arg EDITION=lab -t img-ne-lab-addon:dev .
# Run:    docker compose up   (docker-compose.yml: hardened, loopback-only, NA_ALLOW_NO_TURNSTILE=1 for local use)

FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS build
ARG EDITION=lab
RUN test "$EDITION" = "lab" || { echo "this Dockerfile builds the lab edition only (EDITION=$EDITION)"; exit 1; }
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY --from=ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN UV_NO_CACHE=1 uv export --frozen --format requirements-txt --no-dev --no-emit-project --no-emit-workspace --no-header -o requirements.lock.txt \
 && pip install --require-hashes --no-deps --prefix /install -r requirements.lock.txt
COPY src/network_assessment /install/lib/python3.15/site-packages/network_assessment
RUN find /install -name "__pycache__" -type d -prune -exec rm -rf {} + \
 && python - <<'PY'
import importlib.util, sys
sys.path.insert(0, "/install/lib/python3.15/site-packages")
for forbidden in ("azure", "msal", "boto3"):
    if importlib.util.find_spec(forbidden) is not None:
        raise SystemExit(f"edition boundary: {forbidden} is importable in the build stage")
print("edition boundary: no cloud SDK in /install")
PY

FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS lab
ARG EDITION=lab
RUN test "$EDITION" = "lab"
# The licences of what the image carries, as an SPDX expression: this repository's own code is MIT (LICENSE), and the
# engine wheel installed beside it is Apache-2.0 (its metadata says so; third_party/network-assessment-azure-engine/).
# publish-images.yml sets the other labels at push time; this one never changes between builds, so it lives with the
# image and every build carries it. ci.yml and publish-images.yml fail when the built image carries another value, and
# tests/security/test_image_licences.py when this line, LICENSE or the bundled licence files disagree. The label covers
# the Hybrid Cloud Works code only (this repository MIT, the engine Apache-2.0); the base image, Python and the other
# installed packages keep their own licences, with their texts in .dist-info and /usr/share/doc.
LABEL org.opencontainers.image.licenses="MIT AND Apache-2.0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 \
    NA_STATIC_DIR=/app/web NA_SAMPLES_DIR=/app/samples NA_FRAME_ANCESTORS="'none'" NA_TELEMETRY=0
# Debian's security updates, in a RUN of their own so that a failure fails the build. The base is pinned by digest,
# but a Debian security upload reaches the mirrors days before the official image is rebuilt with it: on 2026-11-05
# the website's Docker Scout gate refused the published image for apt 3.0.3 (CVE-2026-109518, fixed in 3.0.4 from
# trixie-security) while the newest python:3.15-slim-trixie digest still shipped 3.0.3, so no base bump could clear
# it (saulpatinojr/HCW-HybridCloudWorks#1562). `Acquire::Retries=0` on both commands: the apt doing this upgrade is
# still the base's, and CVE-2026-109518 needs a download retry to slip an unverified package in, so the retry path
# stays closed until the upgraded apt is in place (a mirror hiccup fails the build instead of retrying).
# `--error-on=any` fails the update when any index (trixie-security above all) cannot be fetched, instead of
# succeeding with a warning and upgrading nothing. PUBLISH_CACHE_BUST is a per-run value publish-images.yml and
# ci.yml pass (run id and attempt); naming it in the command gives this layer a new cache key on every run, so a
# rebuild of the same commit never reuses an older upgrade result after a newer security upload. Unset on a local
# build, which is fine: the layer is then cached as usual. A successful upgrade is not proof that anything moved
# (a mirror can serve a valid index that lacks the security upload), so the simulated upgrade afterwards must
# report nothing left to do, with no package held back: an image still behind the index it just fetched fails the
# build here. A version floor for one advisory would rot; this holds for every future one. The website's Scout
# check of the published image is the control that names a CVE. tests/security/test_image_security_updates.py
# pins all of this.
ARG PUBLISH_CACHE_BUST=
# The one pipe here already fails closed: a failing `apt-get -s upgrade` prints no "0 upgraded" line, so the
# grep fails the step. pipefail would add a false failure instead (`grep -q` stops reading early), hence (#1575):
# hadolint ignore=DL4006
RUN printf 'security updates, run: %s\n' "${PUBLISH_CACHE_BUST}" \
 && apt-get -o Acquire::Retries=0 update --error-on=any \
 && apt-get -o Acquire::Retries=0 upgrade -y --no-install-recommends \
 && apt-get -o Acquire::Retries=0 -s upgrade | grep -q '^0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded' \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
# pip, ensurepip, setuptools and wheel leave the runtime (nothing installs at run time). The uninstall is allowed to
# fail inside its braces only; before, its `|| true` was unscoped and swallowed a failed apt upgrade too.
RUN { python -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true; } \
 && rm -rf /usr/local/lib/python3.15/ensurepip /usr/local/lib/python3.15/site-packages/pip* \
           /usr/local/lib/python3.15/site-packages/setuptools* /usr/local/lib/python3.15/site-packages/wheel* \
           /usr/local/bin/pip* /usr/local/bin/wheel /root/.cache \
 && groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /install /usr/local
# The licence texts travel with the image (MIT asks for its notice with every copy; Apache-2.0 section 4 for the
# licence and the NOTICE). Root-owned and read-only to uid 10001. third_party/ holds one folder per bundled component,
# so the engine's pair lands in /usr/share/licenses/network-assessment-azure-engine/ (the folder is copied whole so
# that the boundary test, which allows no cloud name on a code line of this file, keeps holding). The engine's pair
# stays even once a wheel that ships its own (engine 0.1.3 and later, in its .dist-info/licenses/) is adopted.
COPY LICENSE NOTICE /usr/share/licenses/hcw-networkeyes-addon/
COPY third_party/ /usr/share/licenses/
COPY --chown=10001:10001 web /app/web
COPY --chown=10001:10001 samples /app/samples
WORKDIR /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).status==200 else 1)"]
CMD ["python", "-m", "network_assessment"]
