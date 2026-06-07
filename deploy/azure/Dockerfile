# syntax=docker/dockerfile:1
#
# UIAO Azure SaaS runtime image (ADR-096).
# Multi-stage: build a wheel-friendly venv, then a slim runtime.
# Entrypoint: uvicorn uiao.saas.asgi:app — the multi-tenant data plane +
# control plane. Runs on Azure Container Apps; the platform terminates TLS
# and reverse-proxies to the container's ingress target port.

# ---- builder ---------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Build deps for asyncpg / cryptography wheels (most ship manylinux wheels,
# but keep gcc available for source fallbacks).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only what's needed to resolve + install the package, to maximise
# layer caching. The package is installed with the [saas] extra.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install ".[saas]"

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    # SaaS defaults — overridden by Container Apps env / Key Vault refs.
    UIAO_SAAS_CLOUD=commercial \
    UIAO_LOG_LEVEL=info \
    PORT=8000

# Non-root runtime user (Container Apps best practice).
RUN groupadd --system uiao && useradd --system --gid uiao --create-home uiao

COPY --from=builder /opt/venv /opt/venv

USER uiao
WORKDIR /home/uiao

EXPOSE 8000

# Container Apps health probe targets /healthz (see bicep ingress config).
# uvicorn binds 0.0.0.0 inside the container; ingress/TLS is the platform's.
CMD ["sh", "-c", "uvicorn uiao.saas.asgi:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*' --log-level ${UIAO_LOG_LEVEL}"]
