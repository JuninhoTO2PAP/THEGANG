# Deploy THE GANG API no Railway (rode apos `railway login`)
# Uso: powershell -ExecutionPolicy Bypass -File deploy/railway-up.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Railway = "npx --yes @railway/cli@latest"

Push-Location $Backend
try {
  Write-Host "==> Verificando login Railway..." -ForegroundColor Cyan
  $who = Invoke-Expression "$Railway whoami 2>&1"
  if ($LASTEXITCODE -ne 0 -or "$who" -match "Unauthorized") {
    throw "Nao autenticado. Rode: npx @railway/cli login"
  }
  Write-Host "Logado: $who"

  if (-not (Test-Path ".railway")) {
    Write-Host "==> Criando projeto..." -ForegroundColor Cyan
    Invoke-Expression "$Railway init --name the-gang-api"
  }

  Write-Host "==> Variaveis de ambiente..." -ForegroundColor Cyan
  $vars = @{
    ENVIRONMENT                  = "production"
    SECRET_KEY                   = "the_gang_railway_$(Get-Random -Maximum 999999)_x9k2m4p7q1w8"
    CORS_ORIGINS                 = "https://gang.httpslaudo.com.br,https://the-gang.pages.dev"
    SEED_ON_BOOT                 = "1"
    BCRYPT_ROUNDS                = "12"
    ACCESS_TOKEN_EXPIRE_MINUTES  = "15"
    REFRESH_TOKEN_EXPIRE_DAYS    = "7"
    LIVEKIT_URL                  = "wss://the-gang-project-ifijvidj.livekit.cloud"
    LIVEKIT_API_KEY              = "APIHqq8vYgdewdA"
    LIVEKIT_API_SECRET           = "ok0D8xNQNnq0fiIlL1CUdinVRvn1z4CWPTyISZNogqE"
    VAPID_CONTACT                = "mailto:admin@httpslaudo.com.br"
  }
  foreach ($k in $vars.Keys) {
    Invoke-Expression "$Railway variables --set `"$k=$($vars[$k])`"" | Out-Null
  }

  Write-Host "==> Postgres (se ainda nao existir)..." -ForegroundColor Cyan
  Invoke-Expression "$Railway add --database postgres" 2>&1 | Out-Host

  Write-Host "==> Deploy..." -ForegroundColor Cyan
  Invoke-Expression "$Railway up --detach"
  Invoke-Expression "$Railway domain" 2>&1 | Out-Host

  Write-Host "==> Status / URL:" -ForegroundColor Green
  Invoke-Expression "$Railway status" 2>&1 | Out-Host
  Invoke-Expression "$Railway domain" 2>&1 | Out-Host
}
finally {
  Pop-Location
}
