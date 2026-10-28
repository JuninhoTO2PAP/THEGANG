# Sobe a API do THE GANG na porta 8000 (para o Tunnel).
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
  Write-Host "Crie o venv antes: py -m venv .venv && .\.venv\Scripts\pip install -r requirements-dev.txt"
  exit 1
}

New-Item -ItemType Directory -Force -Path .\data | Out-Null

# Carrega .env.production se existir
if (Test-Path .\.env.production) {
  Get-Content .\.env.production | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_.Split('=', 2)
    Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim()
  }
} else {
  $env:ENVIRONMENT = "development"
  $env:CORS_ORIGINS = "http://localhost:5173,https://gang.httpslaudo.com.br,https://the-gang.pages.dev"
}

.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.db.seed
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
