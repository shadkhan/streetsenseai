FROM python:3.12-slim

# System deps for psycopg2-binary and geoalchemy2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifest first — changes here invalidate the dep layer only
COPY pyproject.toml uv.lock ./

# Install production deps into the project venv, frozen from lockfile
ENV UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-dev

# Copy application source
COPY . .

# Put the venv's bin directory on PATH so uvicorn/celery are callable directly
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Entrypoint: run migrations then start the server
# Override CMD with "celery ..." to start a worker instead
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
