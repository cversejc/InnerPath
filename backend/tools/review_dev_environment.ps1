$ErrorActionPreference = 'Stop'
$reviewContainer = (docker inspect innerpath-backend | ConvertFrom-Json)[0]
foreach ($entry in $reviewContainer.Config.Env) {
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
$reviewCredentialFile = $env:REVIEW_CREDENTIAL_FILE
if ($reviewCredentialFile -and (Test-Path -LiteralPath $reviewCredentialFile)) {
    foreach ($entry in Get-Content -LiteralPath $reviewCredentialFile) {
        if ($entry -match '^\s*(DEEPSEEK_API_KEY|DEEPSEEK_API_URL|DEEPSEEK_MODEL)\s*=\s*(.*?)\s*$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"').Trim("'"), 'Process')
        }
    }
}
