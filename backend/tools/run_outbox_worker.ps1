param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$RedisUrl = $env:REDIS_URL,
    [string]$ArtifactDirectory
)
$ErrorActionPreference = 'Stop'
$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$workerScript = Join-Path $backendRoot 'tools\run_outbox_worker.py'
if (-not $DatabaseUrl) { throw 'DATABASE_URL is required to start the Outbox worker' }

$existing = @(
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*run_outbox_worker.py*' }
)
if ($existing.Count -gt 0) {
    Write-Output "Outbox worker already running PID=$($existing.ProcessId -join ',')"
    return
}

if (-not $ArtifactDirectory) { $ArtifactDirectory = Join-Path $backendRoot 'logs' }
New-Item -ItemType Directory -Path $ArtifactDirectory -Force | Out-Null
$env:DATABASE_URL = $DatabaseUrl
if ($RedisUrl) { $env:REDIS_URL = $RedisUrl }
$env:PYTHONIOENCODING = 'utf-8'
$worker = Start-Process -FilePath (Join-Path $backendRoot '.venv\Scripts\python.exe') `
    -ArgumentList $workerScript `
    -WorkingDirectory $backendRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $ArtifactDirectory 'outbox-worker.out.log') `
    -RedirectStandardError (Join-Path $ArtifactDirectory 'outbox-worker.err.log') `
    -PassThru
Write-Output "Outbox worker PID=$($worker.Id); log=$(Join-Path $ArtifactDirectory 'outbox-worker.out.log')"
