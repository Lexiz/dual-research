# Spec 0020 — Fly.io deployment image for the dual-research UI server.
#
# Single-stage build: install uv + project deps, copy src, run `dual-research serve`.
# At runtime, Fly sets RUNS_BACKEND=supabase + the supabase secrets via
# `fly secrets set`; the server then reads from Supabase instead of local disk.

# Spec 0159 — pinned to 3.13-slim. The full 3.14 image was ~1.2GB and the
# resulting cold boot routinely exceeded Fly's machines-API observation
# window during rolling deploys (9 consecutive timeouts: handoffs
# 2026-05-22-spec-0141…0150,0153,0156). 3.13-slim drops to ~200MB; faster
# pull, faster extract, smaller import footprint at boot. All direct + key
# transitive deps (anthropic, fastapi, openai, supabase, pyiceberg) have
# shipped 3.13 wheels for months. If a future dep needs to build from
# source, add a minimal `apt-get install -y --no-install-recommends gcc`
# before the first `uv sync` (and clean apt lists in the same RUN).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN pip install --no-cache-dir uv

# Install dependencies first for layer caching: only re-runs when uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Now copy source + install the project itself.
COPY src/ ./src/
COPY README.md ./
# Spec 0126 — bundle the specs/ directory so /api/specs/{spec_id} can serve
# spec markdown for the Changelog tab's "Open spec ↗" modal.
COPY specs/ ./specs/
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "dual-research", "serve", "--host", "0.0.0.0", "--port", "8080"]
