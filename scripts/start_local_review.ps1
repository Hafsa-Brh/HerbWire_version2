[CmdletBinding()]
param(
    [ValidatePattern('^[a-z0-9_]+$')]
    [string]$DatabaseName = 'herbwire_m4c_demo_20260902'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$StateRoot = Join-Path $env:TEMP 'herbwire-local-review'
$ProtectedDatabases = @(
    'herbwire',
    'herbwire_staging_transfer',
    'herbwire_m4b_demo_20260902',
    'herbwire_m4a_review_20260902'
)

if ($DatabaseName -in $ProtectedDatabases) {
    throw 'Refusing to start review services against a protected database.'
}
foreach ($Port in 8000, 5173) {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port already has a listener; identify and stop it before starting."
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot '.env'))) {
    throw 'The ignored repository-root .env is required.'
}

New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
$env:HERBWIRE_ENVIRONMENT = 'local'
$env:HERBWIRE_LOCAL_DATABASE_NAME = $DatabaseName
$env:HERBWIRE_FRONTEND_ORIGIN = 'http://127.0.0.1:5173'
$env:HERBWIRE_ENABLE_DEVELOPMENT_ENDPOINTS = 'false'
$Backend = Start-Process -FilePath (Join-Path $RepoRoot '.venv\Scripts\python.exe') `
    -ArgumentList '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000' `
    -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $StateRoot 'backend-out.log') `
    -RedirectStandardError (Join-Path $StateRoot 'backend-error.log')

$env:VITE_HERBWIRE_API_BASE_URL = 'http://127.0.0.1:8000'
$Frontend = Start-Process -FilePath (Get-Command 'node.exe').Source `
    -ArgumentList (Join-Path $RepoRoot 'frontend\node_modules\vite\bin\vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort' `
    -WorkingDirectory (Join-Path $RepoRoot 'frontend') -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $StateRoot 'frontend-out.log') `
    -RedirectStandardError (Join-Path $StateRoot 'frontend-error.log')

try {
    $Deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $BackendListener = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
        $FrontendListener = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    } until (($BackendListener -and $FrontendListener) -or (Get-Date) -gt $Deadline)
    if (-not $BackendListener -or -not $FrontendListener) {
        throw 'The review listeners did not start within 30 seconds.'
    }
    $Health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health'
    $Plants = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/plants?page=1&page_size=50'
    if ($Health.status -ne 'ok' -or $Health.database -ne 'connected' -or $Plants.total -ne 30) {
        throw 'Startup verification failed health, database, or 30-profile checks.'
    }
    $BackendPid = [int]($BackendListener | Select-Object -First 1 -ExpandProperty OwningProcess)
    $FrontendPid = [int]($FrontendListener | Select-Object -First 1 -ExpandProperty OwningProcess)
    [pscustomobject]@{
        backend_listener_pid = $BackendPid
        frontend_listener_pid = $FrontendPid
        backend_launcher_pid = $Backend.Id
        frontend_launcher_pid = $Frontend.Id
        database_name = $DatabaseName
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $StateRoot 'processes.json') -Encoding utf8
    Write-Output "Backend listener PID: $BackendPid"
    Write-Output "Frontend listener PID: $FrontendPid"
    Write-Output 'Health connected; public plant total: 30.'
}
catch {
    if (-not $Frontend.HasExited) { Stop-Process -Id $Frontend.Id }
    if (-not $Backend.HasExited) { Stop-Process -Id $Backend.Id }
    throw
}
finally {
    Remove-Item Env:HERBWIRE_LOCAL_DATABASE_NAME -ErrorAction SilentlyContinue
    Remove-Item Env:VITE_HERBWIRE_API_BASE_URL -ErrorAction SilentlyContinue
}
