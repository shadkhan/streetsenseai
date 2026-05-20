#!/bin/sh
set -e

# Run database migrations before starting the server.
# On a fresh deploy this applies all pending Alembic revisions.
# On a no-op deploy this exits instantly.
echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

exec "$@"
