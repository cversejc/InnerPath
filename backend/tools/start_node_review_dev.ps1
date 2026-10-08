param([string]$ArtifactDirectory)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backendRoot = Join-Path $repoRoot 'backend'

function Get-FreeLocalPort([int]$Start, [int]$End) {
    foreach ($candidate in $Start..$End) {
        $listener = Get-NetTCPConnection -LocalPort $candidate -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $listener) { return $candidate }
    }
    throw "No free local port in range $Start-$End"
}

# Reuse the development container's configured credentials without printing them.
$container = (docker inspect innerpath-backend | ConvertFrom-Json)[0]
foreach ($entry in $container.Config.Env) {
    $pair = $entry.Split('=', 2)
    if ($pair[0] -in @('DATABASE_URL','REDIS_URL','SECRET_KEY','LLM_CONFIG_ENCRYPTION_KEY','DEEPSEEK_API_KEY','DEEPSEEK_API_URL','DEEPSEEK_MODEL','ENVIRONMENT')) {
        [Environment]::SetEnvironmentVariable($pair[0], $pair[1], 'Process')
    }
}
$env:DATABASE_URL = $env:DATABASE_URL.Replace('@postgres:5432/', '@127.0.0.1:5433/')
$env:REDIS_URL = $env:REDIS_URL.Replace('redis://redis:', 'redis://127.0.0.1:')
$env:DEBUG = 'false'
$env:ENVIRONMENT = 'development'
$env:PYTHONIOENCODING = 'utf-8'
$apiPort = Get-FreeLocalPort 8001 8099
$frontendPort = Get-FreeLocalPort 3011 3099
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:$apiPort"
if (-not $ArtifactDirectory) { throw 'ArtifactDirectory is required' }
New-Item -ItemType Directory -Path $ArtifactDirectory -Force | Out-Null
Push-Location $backendRoot
try {
    & '.\.venv\Scripts\python.exe' -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
    & '.\.venv\Scripts\python.exe' tools\migrate_node_reviews.py > (Join-Path $ArtifactDirectory 'migration-impact.json')
    if ($LASTEXITCODE -ne 0) { throw 'Impact inventory failed' }
    & '.\.venv\Scripts\python.exe' tools\migrate_node_reviews.py --apply > (Join-Path $ArtifactDirectory 'migration-applied.json')
    if ($LASTEXITCODE -ne 0) { throw 'Policy migration failed' }
    $api = Start-Process -FilePath (Join-Path $backendRoot '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$apiPort" -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ArtifactDirectory 'backend.log') -RedirectStandardError (Join-Path $ArtifactDirectory 'backend-error.log') -PassThru
} finally { Pop-Location }
$configPath = Join-Path $ArtifactDirectory 'vite.review.config.mjs'
$importPath = 'file:///' + (Join-Path $repoRoot 'vite.config.js').Replace('\','/')
Set-Content -LiteralPath $configPath -Encoding utf8 -Value "import config from '$importPath'; export default { ...config, server: { ...config.server, open: false, host: '127.0.0.1', port: $frontendPort, strictPort: true } };"
$vite = Start-Process -FilePath (Get-Command node).Source -ArgumentList (Join-Path $repoRoot 'node_modules\vite\bin\vite.js'), '--config', $configPath -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ArtifactDirectory 'frontend.log') -RedirectStandardError (Join-Path $ArtifactDirectory 'frontend-error.log') -PassThru
Write-Output "Review development API PID=$($api.Id) on port $apiPort, frontend PID=$($vite.Id); frontend http://127.0.0.1:$frontendPort"
