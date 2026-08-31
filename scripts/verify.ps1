$ErrorActionPreference = "Stop"

function Assert-LastExit {
    param([string]$CommandName)

    if ($LASTEXITCODE -ne 0) {
        throw "$CommandName failed with exit code $LASTEXITCODE."
    }
}

function Assert-DisposableDatabaseName {
    param([string]$DatabaseName)

    if ([string]::IsNullOrWhiteSpace($DatabaseName) -or $DatabaseName -ne "herbwire_m2_migration_verify") {
        throw "Refusing to continue because the disposable database target is not exactly herbwire_m2_migration_verify."
    }
}

function Invoke-PostgresScalar {
    param(
        [string]$DatabaseName,
        [string]$Sql
    )

    $result = docker compose exec -T postgres psql -U herbwire -d $DatabaseName -tA -v ON_ERROR_STOP=1 -c $Sql
    Assert-LastExit "psql $DatabaseName"
    return ($result | Out-String).Trim()
}

function Assert-ConnectedDatabaseName {
    param(
        [string]$DatabaseName,
        [string]$ExpectedName
    )

    $actualName = Invoke-PostgresScalar -DatabaseName $DatabaseName -Sql "SELECT current_database();"
    if ($actualName -ne $ExpectedName) {
        throw "Connected database name mismatch. Expected $ExpectedName but found $actualName."
    }
}

$python = Resolve-Path ".\.venv\Scripts\python.exe"
$verificationDatabaseName = "herbwire_m2_migration_verify"
$postgresPassword = if ($env:HERBWIRE_POSTGRES_PASSWORD -and $env:HERBWIRE_POSTGRES_PASSWORD.Trim().Length -gt 0) {
    $env:HERBWIRE_POSTGRES_PASSWORD.Trim()
} else {
    "herbwire_dev"
}

Assert-DisposableDatabaseName $verificationDatabaseName
$env:HERBWIRE_POSTGRES_PORT = "5433"
$env:HERBWIRE_ALLOW_DESTRUCTIVE_TEST_DB = "true"
$env:HERBWIRE_DATABASE_URL = "postgresql+psycopg://herbwire:${postgresPassword}@127.0.0.1:5433/$verificationDatabaseName"

Write-Host "Validating Docker Compose configuration..."
docker compose config | Out-Null
Assert-LastExit "docker compose config"

Write-Host "Starting PostgreSQL..."
docker compose up -d postgres | Out-Null
Assert-LastExit "docker compose up -d postgres"

for ($attempt = 1; $attempt -le 30; $attempt++) {
    docker compose exec -T postgres pg_isready -U herbwire -d herbwire | Out-Null
    if ($LASTEXITCODE -eq 0) {
        break
    }
    Start-Sleep -Seconds 2
    if ($attempt -eq 30) {
        throw "PostgreSQL did not become ready in time."
    }
}

Assert-ConnectedDatabaseName -DatabaseName "postgres" -ExpectedName "postgres"

Write-Host "Resetting disposable verification database..."
Assert-DisposableDatabaseName $verificationDatabaseName
$existingDisposableDatabase = Invoke-PostgresScalar -DatabaseName "postgres" -Sql "SELECT datname FROM pg_database WHERE datname = '$verificationDatabaseName';"
if ($existingDisposableDatabase -eq $verificationDatabaseName) {
    Assert-DisposableDatabaseName $existingDisposableDatabase
    docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$verificationDatabaseName' AND pid <> pg_backend_pid();" | Out-Null
    Assert-LastExit "terminate disposable database sessions"
}
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $verificationDatabaseName;" | Out-Null
Assert-LastExit "drop disposable verification database"
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $verificationDatabaseName;" | Out-Null
Assert-LastExit "create disposable verification database"
Assert-ConnectedDatabaseName -DatabaseName $verificationDatabaseName -ExpectedName $verificationDatabaseName

Write-Host "Running backend verification..."
& $python -m ruff check backend
Assert-LastExit "ruff check backend"
& $python -m ruff format --check backend
Assert-LastExit "ruff format --check backend"
& $python -m alembic -c backend/alembic.ini current
Assert-LastExit "alembic current"
& $python -m alembic -c backend/alembic.ini upgrade head
Assert-LastExit "alembic upgrade head"
& $python -m pytest backend/tests -q
Assert-LastExit "pytest backend/tests -q"
& $python -m alembic -c backend/alembic.ini downgrade 20260829_0001
Assert-LastExit "alembic downgrade 20260829_0001"
& $python -m alembic -c backend/alembic.ini upgrade head
Assert-LastExit "alembic upgrade head"

Write-Host "Running frontend verification..."
Push-Location frontend
npm run lint
Assert-LastExit "npm run lint"
npm run test
Assert-LastExit "npm run test"
npm run typecheck
Assert-LastExit "npm run typecheck"
npm run build
Assert-LastExit "npm run build"
Pop-Location

Write-Host "Removing disposable verification database..."
Assert-DisposableDatabaseName $verificationDatabaseName
Assert-ConnectedDatabaseName -DatabaseName "postgres" -ExpectedName "postgres"
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$verificationDatabaseName' AND pid <> pg_backend_pid();" | Out-Null
Assert-LastExit "terminate disposable database sessions"
docker compose exec -T postgres psql -U herbwire -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $verificationDatabaseName;" | Out-Null
Assert-LastExit "drop disposable verification database"
