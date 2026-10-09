param([Parameter(Mandatory=$true)][string]$ArtifactDirectory)
$ErrorActionPreference = 'Stop'
$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'review_dev_environment.ps1')
$listeners = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    if ($process.CommandLine -notmatch 'uvicorn app\.main:app' -or $process.CommandLine -notmatch '--port 8001') { throw 'Port 8001 belongs to another service' }
    Stop-Process -Id $process.ProcessId -Force
}
$api = Start-Process -FilePath (Join-Path $backendRoot '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001' -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ArtifactDirectory 'backend.log') -RedirectStandardError (Join-Path $ArtifactDirectory 'backend-error.log') -PassThru
Write-Output "Review API launcher PID=$($api.Id)"
& (Join-Path $PSScriptRoot 'run_outbox_worker.ps1') -ArtifactDirectory $ArtifactDirectory
