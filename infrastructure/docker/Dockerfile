# Stage 1: Builder
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=$SETUPTOOLS_SCM_PRETEND_VERSION

COPY --from=ghcr.io/astral-sh/uv:0.11.9 /uv /usr/local/bin/uv
ENV PATH="/usr/local/bin:${PATH}"

# Install all workspace packages + test extras into /app/.venv in a single locked pass.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv --relocatable && \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    uv sync --frozen --no-group docs --all-packages --extra test

# Pre-compile governance artifacts so tests don't rebuild from a different source path
ENV PATH="/app/.venv/bin:${PATH}"
RUN sdd governance compile

# Stage 2: Runtime
FROM python:3.14-slim

LABEL org.opencontainers.image.title="SDD Agentic OS" \
      org.opencontainers.image.description="Professional AI-first Agentic Operating System Architecture" \
      org.opencontainers.image.vendor="sdd-harness" \
      org.opencontainers.image.version="1.0.0"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    tini \
    openssl \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy uv for the `uv run` fallback path in the Makefile.
COPY --from=ghcr.io/astral-sh/uv:0.11.9 /uv /usr/local/bin/uv

RUN groupadd -g 1000 sdd && \
    useradd -u 1000 -g sdd -m -s /bin/bash sdd

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=sdd:sdd . /app

# Overlay pre-compiled governance artifacts from builder (not in git)
COPY --from=builder --chown=sdd:sdd /app/.sdd/compiled /app/.sdd/compiled

COPY --chown=sdd:sdd infrastructure/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chown sdd:sdd /app && \
    ln -s /app/.venv /venv

# /app/.venv/bin first so Python and all tools resolve from the pre-built venv.
# VIRTUAL_ENV points to the project-local virtualenv used by the runtime container.
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}" \
    VIRTUAL_ENV=/app/.venv

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

USER sdd
CMD []

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sdd --help || exit 1
