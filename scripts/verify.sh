#!/usr/bin/env bash
set -euo pipefail

assert_disposable_database_name() {
  local database_name="$1"
  if [ -z "$database_name" ] || [ "$database_name" != "herbwire_m2_migration_verify" ]; then
    printf 'Refusing to continue because the disposable database target is not exactly herbwire_m2_migration_verify.\n' >&2
    exit 1
  fi
}

postgres_scalar() {
  local database_name="$1"
  local sql="$2"
  docker compose exec -T postgres psql -U herbwire -d "$database_name" -tA -v ON_ERROR_STOP=1 -c "$sql" | tr -d '\r' | sed 's/[[:space:]]*$//'
}

assert_connected_database_name() {
  local database_name="$1"
  local expected_name="$2"
  local actual_name
  actual_name="$(postgres_scalar "$database_name" 'SELECT current_database();')"
  if [ "$actual_name" != "$expected_name" ]; then
    printf 'Connected database name mismatch. Expected %s but found %s.\n' "$expected_name" "$actual_name" >&2
    exit 1
  fi
}

if [ -x "./.venv/bin/python" ]; then
  PYTHON_BIN="./.venv/bin/python"
elif [ -f "./.venv/Scripts/python.exe" ]; then
  PYTHON_BIN="./.venv/Scripts/python.exe"
else
  printf 'Repository virtual environment not found. Expected ./.venv/bin/python or ./.venv/Scripts/python.exe.\n' >&2
  exit 1
fi

VERIFICATION_DATABASE_NAME="herbwire_m2_migration_verify"
POSTGRES_PASSWORD="${HERBWIRE_POSTGRES_PASSWORD:-herbwire_dev}"
assert_disposable_database_name "$VERIFICATION_DATABASE_NAME"

export HERBWIRE_POSTGRES_PORT="5433"
export HERBWIRE_ALLOW_DESTRUCTIVE_TEST_DB="true"
export HERBWIRE_DATABASE_URL="postgresql+psycopg://herbwire:${POSTGRES_PASSWORD}@127.0.0.1:5433/${VERIFICATION_DATABASE_NAME}"

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

assert_connected_database_name "postgres" "postgres"

printf 'Resetting disposable verification database...\n'
existing_disposable_database="$(postgres_scalar "postgres" "SELECT datname FROM pg_database WHERE datname = '${VERIFICATION_DATABASE_NAME}';")"
if [ "$existing_disposable_database" = "$VERIFICATION_DATABASE_NAME" ]; then
  assert_disposable_database_name "$existing_disposable_database"
  docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${VERIFICATION_DATABASE_NAME}' AND pid <> pg_backend_pid();" >/dev/null
fi
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${VERIFICATION_DATABASE_NAME};" >/dev/null
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${VERIFICATION_DATABASE_NAME};" >/dev/null
assert_connected_database_name "$VERIFICATION_DATABASE_NAME" "$VERIFICATION_DATABASE_NAME"

printf 'Running backend verification...\n'
"$PYTHON_BIN" -m ruff check backend
"$PYTHON_BIN" -m ruff format --check backend
"$PYTHON_BIN" -m alembic -c backend/alembic.ini current
"$PYTHON_BIN" -m alembic -c backend/alembic.ini upgrade head
"$PYTHON_BIN" -m pytest backend/tests -q
"$PYTHON_BIN" -m alembic -c backend/alembic.ini downgrade 20260829_0001
"$PYTHON_BIN" -m alembic -c backend/alembic.ini upgrade head

printf 'Running frontend verification...\n'
(
  cd frontend
  npm run lint
  npm run test
  npm run typecheck
  npm run build
)

printf 'Removing disposable verification database...\n'
assert_disposable_database_name "$VERIFICATION_DATABASE_NAME"
assert_connected_database_name "postgres" "postgres"
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${VERIFICATION_DATABASE_NAME}' AND pid <> pg_backend_pid();" >/dev/null
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS ${VERIFICATION_DATABASE_NAME};" >/dev/null
