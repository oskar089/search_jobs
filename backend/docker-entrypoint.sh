#!/bin/bash
set -e

echo "========================================"
echo "  Search Jobs Backend — Docker Entrypoint"
echo "========================================"

# Wait for PostgreSQL to be ready
echo "==> Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U searchjobs -q 2>/dev/null; do
  echo "    PostgreSQL not ready yet... sleeping"
  sleep 2
done
echo "    PostgreSQL is ready!"

# Run Alembic migrations
echo "==> Running Alembic migrations..."
alembic upgrade head
echo "    Migrations completed!"

echo "==> Starting service..."
echo ""
exec "$@"
