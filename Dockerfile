# Spec 0020 — Fly.io deployment image for the dual-research UI server.
#
# Single-stage build: install uv + project deps, copy src, run `dual-research serve`.
# At runtime, Fly sets RUNS_BACKEND=supabase + the supabase secrets via
# `fly secrets set`; the server then reads from Supabase instead of local disk.

# Using the full python image (not -slim) because supabase-py pulls in
# pyiceberg, which has no Python 3.14 wheel as of writing and needs gcc to
# build from source. Revisit once pyiceberg ships a 3.14 wheel.
FROM python:3.14

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
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "dual-research", "serve", "--host", "0.0.0.0", "--port", "8080"]
