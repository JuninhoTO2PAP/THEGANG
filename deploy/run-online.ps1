# Mantém API + tunnel Cloudflare no ar para https://gang.httpslaudo.com.br
# Uso: clique direito → Executar com PowerShell (deixe a janela aberta)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cf)) { $cf = "C:\Program Files\cloudflared\cloudflared.exe" }
if (-not (Test-Path $cf)) { throw "cloudflared não encontrado. Instale: winget install Cloudflare.cloudflared" }

# API
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object {
  Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

if (Test-Path "$root\backend\.env.production") {
  Get-Content "$root\backend\.env.production" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_.Split('=', 2)
    Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim()
  }
}

Set-Location "$root\backend"
New-Item -ItemType Directory -Force -Path .\data | Out-Null
.\.venv\Scripts\python.exe -m alembic upgrade head | Out-Null
$env:ENVIRONMENT = "development"
.\.venv\Scripts\python.exe -m app.db.seed | Out-Null
$env:ENVIRONMENT = "production"
$env:ALLOW_SQLITE = "true"

Write-Host "API em http://127.0.0.1:8000 ..."
Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory "$root\backend" -WindowStyle Minimized
Start-Sleep -Seconds 2

Write-Host "Tunnel Cloudflare (deixe esta janela aberta)..."
Write-Host "Se a URL do tunnel mudar, atualize FALLBACK_API_ORIGIN em frontend/functions e rode: npm run deploy"
& $cf tunnel --url http://127.0.0.1:8000 --no-autoupdate
