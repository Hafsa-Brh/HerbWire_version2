[CmdletBinding()]
param(
    [ValidatePattern('^[a-z0-9_]+$')]
    [string]$DatabaseName = 'herbwire_m4c_demo_20260902'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvPath = Join-Path $RepoRoot '.env'
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
if (-not (Test-Path -LiteralPath $EnvPath)) {
    throw 'The ignored repository-root .env is required.'
}

function Get-RequiredDotEnvValue {
    param([string]$Name)

    $Prefix = "$Name="
    $Matches = @(
        [IO.File]::ReadAllLines($EnvPath) |
            Where-Object { $_.StartsWith($Prefix, [StringComparison]::Ordinal) }
    )
    if ($Matches.Count -ne 1) {
        throw "The repository-root .env must contain exactly one $Name entry."
    }
    $Value = $Matches[0].Substring($Prefix.Length)
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -ne $Value.Trim()) {
        throw "The repository-root .env contains an invalid $Name value."
    }
    return $Value
}

function Stop-StartedHerbWireListener {
    param([int]$Port)

    $Listeners = @(
        Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port `
            -State Listen -ErrorAction SilentlyContinue
    )
    foreach ($Listener in $Listeners) {
        $Process = Get-CimInstance Win32_Process `
            -Filter "ProcessId=$($Listener.OwningProcess)" -ErrorAction SilentlyContinue
        if ($Process.CommandLine -and $Process.CommandLine.Contains($RepoRoot)) {
            Stop-Process -Id $Listener.OwningProcess -ErrorAction SilentlyContinue
        }
    }
}

$AdminEmail = Get-RequiredDotEnvValue 'HERBWIRE_ADMIN_EMAIL'
$AdminPassword = Get-RequiredDotEnvValue 'HERBWIRE_ADMIN_PASSWORD'
if ($AdminEmail -cne 'admin@herbwire2.news') {
    throw 'The local Editorial Desk email does not match the owner-approved account.'
}
if ($AdminPassword.Length -lt 16) {
    throw 'The local Editorial Desk password must contain at least 16 characters.'
}

New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
$OriginalHerbWireEnvironment = @{}
Get-ChildItem Env: | Where-Object { $_.Name -like 'HERBWIRE_*' } | ForEach-Object {
    $OriginalHerbWireEnvironment[$_.Name] = $_.Value
    [Environment]::SetEnvironmentVariable($_.Name, $null, 'Process')
}
$HadOriginalViteApiBase = Test-Path Env:VITE_HERBWIRE_API_BASE_URL
$OriginalViteApiBase = $env:VITE_HERBWIRE_API_BASE_URL
$env:HERBWIRE_ENVIRONMENT = 'local'
$env:HERBWIRE_LOCAL_DATABASE_NAME = $DatabaseName
$env:HERBWIRE_FRONTEND_ORIGIN = 'http://127.0.0.1:5173'
$env:HERBWIRE_ENABLE_DEVELOPMENT_ENDPOINTS = 'false'

try {
    $Backend = Start-Process -FilePath (Join-Path $RepoRoot '.venv\Scripts\python.exe') `
        -ArgumentList '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $StateRoot 'backend-out.log') `
        -RedirectStandardError (Join-Path $StateRoot 'backend-error.log')

    $Deadline = (Get-Date).AddSeconds(45)
    $Health = $null
    do {
        Start-Sleep -Milliseconds 500
        $BackendListener = @(
            Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8000 `
                -State Listen -ErrorAction SilentlyContinue
        )
        if ($BackendListener.Count -eq 1) {
            try {
                $Health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health'
            }
            catch {
                $Health = $null
            }
        }
    } until (($Health -and $Health.status -eq 'ok' -and $Health.database -eq 'connected') -or (Get-Date) -gt $Deadline)
    if (-not $Health -or $Health.status -ne 'ok' -or $Health.database -ne 'connected') {
        throw 'The backend did not reach connected health within 45 seconds.'
    }

    $Plants = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/plants?page=1&page_size=50'
    if ($Plants.total -ne 30) {
        throw 'Startup verification failed the 30-profile check.'
    }

    $LoginSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $LoginPayload = @{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json -Compress
    $Login = Invoke-WebRequest -UseBasicParsing `
        -Uri 'http://127.0.0.1:8000/api/v1/auth/login' -Method Post `
        -ContentType 'application/json' -Body $LoginPayload `
        -Headers @{ Origin = 'http://127.0.0.1:5173' } -WebSession $LoginSession
    if ($Login.StatusCode -ne 200) {
        throw 'The exact repository-root Editorial Desk credentials did not authenticate.'
    }
    $Editorial = Invoke-WebRequest -UseBasicParsing `
        -Uri 'http://127.0.0.1:8000/api/v1/admin/discovery/reviews?page=1&page_size=50' `
        -Headers @{ Origin = 'http://127.0.0.1:5173' } -WebSession $LoginSession
    if ($Editorial.StatusCode -ne 200) {
        throw 'The authenticated Editorial Desk session could not access Discovery Review.'
    }

    $env:VITE_HERBWIRE_API_BASE_URL = 'http://127.0.0.1:8000'
    $Frontend = Start-Process -FilePath (Get-Command 'node.exe').Source `
        -ArgumentList (Join-Path $RepoRoot 'frontend\node_modules\vite\bin\vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort' `
        -WorkingDirectory (Join-Path $RepoRoot 'frontend') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $StateRoot 'frontend-out.log') `
        -RedirectStandardError (Join-Path $StateRoot 'frontend-error.log')

    $Deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $FrontendListener = @(
            Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 5173 `
                -State Listen -ErrorAction SilentlyContinue
        )
    } until (($FrontendListener.Count -eq 1) -or (Get-Date) -gt $Deadline)
    if ($FrontendListener.Count -ne 1) {
        throw 'Vite did not establish exactly one listener within 30 seconds.'
    }

    $FrontendHome = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5173/'
    if ($FrontendHome.StatusCode -ne 200) {
        throw 'The browser-facing frontend did not return HTTP 200.'
    }

    $BackendListener = @(
        Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8000 `
            -State Listen -ErrorAction SilentlyContinue
    )
    if ($BackendListener.Count -ne 1) {
        throw 'The backend does not have exactly one listener.'
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
    Write-Output 'Health connected; public plant total: 30; Editorial Desk login verified.'
}
catch {
    Stop-StartedHerbWireListener 5173
    Stop-StartedHerbWireListener 8000
    throw
}
finally {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'HERBWIRE_*' } | ForEach-Object {
        [Environment]::SetEnvironmentVariable($_.Name, $null, 'Process')
    }
    foreach ($Entry in $OriginalHerbWireEnvironment.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($Entry.Key, $Entry.Value, 'Process')
    }
    if ($HadOriginalViteApiBase) {
        $env:VITE_HERBWIRE_API_BASE_URL = $OriginalViteApiBase
    }
    else {
        Remove-Item Env:VITE_HERBWIRE_API_BASE_URL -ErrorAction SilentlyContinue
    }
    $AdminEmail = $null
    $AdminPassword = $null
    $LoginPayload = $null
}
