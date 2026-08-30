#!/usr/bin/env bash
set -euo pipefail

if [ -x "./.venv/bin/python" ]; then
  PYTHON_BIN="./.venv/bin/python"
elif [ -f "./.venv/Scripts/python.exe" ]; then
  PYTHON_BIN="./.venv/Scripts/python.exe"
else
  printf 'Repository virtual environment not found. Expected ./.venv/bin/python or ./.venv/Scripts/python.exe.\n' >&2
  exit 1
fi

export HERBWIRE_POSTGRES_PORT="5433"
export HERBWIRE_DATABASE_URL="postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5433/herbwire"

printf 'Validating Docker Compose configuration...\n'
docker compose config >/dev/null

printf 'Starting PostgreSQL...\n'
docker compose up -d postgres >/dev/null

for attempt in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U herbwire -d herbwire >/dev/null; then
    break
  fi

  sleep 2

  if [ "$attempt" -eq 30 ]; then
    printf 'PostgreSQL did not become ready in time.\n' >&2
    exit 1
  fi
done

printf 'Running backend verification...\n'
"$PYTHON_BIN" -m ruff check backend
"$PYTHON_BIN" -m ruff format --check backend
"$PYTHON_BIN" -m alembic -c backend/alembic.ini current
"$PYTHON_BIN" -m alembic -c backend/alembic.ini upgrade head
"$PYTHON_BIN" -m pytest backend/tests -q
"$PYTHON_BIN" -m alembic -c backend/alembic.ini downgrade base
"$PYTHON_BIN" -m alembic -c backend/alembic.ini upgrade head

printf 'Running frontend verification...\n'
(
  cd frontend
  npm run lint
  npm run test
  npm run typecheck
  npm run build
)