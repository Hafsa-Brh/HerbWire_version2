$ErrorActionPreference = "Stop"

function Assert-LastExit {
    param([string]$CommandName)

    if ($LASTEXITCODE -ne 0) {
        throw "$CommandName failed with exit code $LASTEXITCODE."
    }
}

$python = Resolve-Path ".\.venv\Scripts\python.exe"
$env:HERBWIRE_POSTGRES_PORT = "5433"
$env:HERBWIRE_DATABASE_URL = "postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5433/herbwire"

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

Write-Host "Running backend verification..."
& $python -m ruff check backend
Assert-LastExit "ruff check backend"
& $python -m ruff format --check backend
Assert-LastExit "ruff format --check backend"
& $python -m alembic -c backend/alembic.ini upgrade head
Assert-LastExit "alembic upgrade head"
& $python -m pytest backend/tests -q
Assert-LastExit "pytest backend/tests -q"
& $python -m alembic -c backend/alembic.ini downgrade base
Assert-LastExit "alembic downgrade base"
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