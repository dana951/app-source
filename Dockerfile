ARG UV_VERSION="0.11.7"

# ---------- Builder ----------
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:3.11-slim AS builder

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy everything needed for install
COPY pyproject.toml uv.lock ./
COPY src ./src

# Single install (deps + project + console script)
RUN uv sync --frozen --no-dev

# ---------- Runtime ----------
FROM python:3.11-slim

WORKDIR /app

RUN useradd --uid 1000 --create-home appuser

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

COPY src ./src

ARG APP_VERSION=unknown
ARG GIT_SHA=unknown
ENV APP_VERSION=${APP_VERSION}
ENV GIT_SHA=${GIT_SHA}

USER appuser

CMD ["podinfo"]