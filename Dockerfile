# syntax=docker/dockerfile:1

ARG CASDOOR_VERSION=4.30.0

# ---------- Stage 1: builder ----------
FROM ghcr.io/astral-sh/uv:0.13.9-python3.13-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONPATH=/app/src

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source for import at runtime. The project metadata files are excluded from
# the Docker context, so install only the locked runtime dependencies above.
COPY src/ ./src/

# Use the official image at the same pinned version for its binary and web assets.
FROM docker.io/casbin/casdoor:v${CASDOOR_VERSION} AS casdoor

# ---------- Stage 2: runtime ----------
FROM docker.io/library/python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/src

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      bash \
      caddy \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 appgroup \
 && useradd --system --uid 10001 --gid appgroup --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src /app/src

RUN mkdir -p /app/casdoor/conf /app/casdoor/data /app/logs \
 && ln -s /app/casdoor/conf /app/conf \
 && chown -R appuser:appgroup /app/casdoor /app/logs

COPY --from=casdoor --chown=appuser:appgroup /server /app/casdoor/casdoor
COPY --from=casdoor --chown=appuser:appgroup /web/build /app/web/build
COPY --from=casdoor --chown=appuser:appgroup /swagger /app/swagger
COPY --chown=appuser:appgroup docker/casdoor/app.conf /app/casdoor/conf/app.conf
COPY --chown=appuser:appgroup docker/casdoor/init_data.json.template /app/casdoor/conf/init_data.json.template
COPY --chown=appuser:appgroup docker/Caddyfile /etc/caddy/Caddyfile
RUN caddy fmt --overwrite /etc/caddy/Caddyfile
COPY --chown=appuser:appgroup docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

USER appuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:80/health', timeout=3)" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
