# Network Assessment lab edition image: docker.io/hybridcloudworks/img-ne-lab-addon
#
# Two stages on one digest-pinned base (infrastructure/docker/versions.env; CI checks every FROM against it).
#   build  exports the hash-pinned third-party set from uv.lock (`uv export --frozen`, with the uv CI uses, by
#          digest; nothing resolves, and uv never reaches the lab stage), installs it into /install with
#          pip --require-hashes --no-deps (nothing resolves beyond the lock), then places the lab application
#          (which carries the ported engine, ADR-0001) beside them as a source tree, so no build backend enters
#          the image.
#   lab    the runtime: apt upgrade, /install copied in, pip/ensurepip/setuptools removed, uid 10001, read-only
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

FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS build
ARG EDITION=lab
RUN test "$EDITION" = "lab" || { echo "this Dockerfile builds the lab edition only (EDITION=$EDITION)"; exit 1; }
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY --from=ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN UV_NO_CACHE=1 uv export --frozen --format requirements-txt --no-dev --no-emit-project --no-emit-workspace --no-header -o requirements.lock.txt \
 && pip install --require-hashes --no-deps --prefix /install -r requirements.lock.txt
COPY src/network_assessment /install/lib/python3.14/site-packages/network_assessment
RUN find /install -name "__pycache__" -type d -prune -exec rm -rf {} + \
 && python - <<'PY'
import importlib.util, sys
sys.path.insert(0, "/install/lib/python3.14/site-packages")
for forbidden in ("azure", "msal", "boto3"):
    if importlib.util.find_spec(forbidden) is not None:
        raise SystemExit(f"edition boundary: {forbidden} is importable in the build stage")
print("edition boundary: no cloud SDK in /install")
PY

FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS lab
ARG EDITION=lab
RUN test "$EDITION" = "lab"
# The licence of this repository's LICENSE file, as an SPDX id. publish-images.yml sets the other labels at push time;
# this one never changes between builds, so it lives with the image and every build carries it. ci.yml fails when the
# built image lacks it or LICENSE stops being the MIT License.
LABEL org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 \
    NA_STATIC_DIR=/app/web NA_SAMPLES_DIR=/app/samples NA_FRAME_ANCESTORS="'none'" NA_TELEMETRY=0
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true \
 && rm -rf /usr/local/lib/python3.14/ensurepip /usr/local/lib/python3.14/site-packages/pip* \
           /usr/local/lib/python3.14/site-packages/setuptools* /usr/local/lib/python3.14/site-packages/wheel* \
           /usr/local/bin/pip* /usr/local/bin/wheel /root/.cache \
 && groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /install /usr/local
COPY --chown=10001:10001 web /app/web
COPY --chown=10001:10001 samples /app/samples
WORKDIR /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).status==200 else 1)"]
CMD ["python", "-m", "network_assessment"]
