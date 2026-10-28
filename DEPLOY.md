# Deploy THE GANG — `gang.httpslaudo.com.br`

## Arquitetura

```text
Browser → https://gang.httpslaudo.com.br  (Cloudflare Pages + PWA)
              ├─ estáticos (HTML/JS/CSS)
              └─ /api e /uploads  → proxy → API_ORIGIN
API      → https://api-gang.httpslaudo.com.br  (Cloudflare Tunnel → FastAPI)
Voz      → LiveKit Cloud
```

DNS (já na Cloudflare):

| Nome | Tipo | Destino |
|------|------|---------|
| `gang` | CNAME | `the-gang.pages.dev` (Proxied) |
| `api-gang` | CNAME | `<tunnel-id>.cfargotunnel.com` (Proxied) |

## 1) Front (Pages)

```powershell
cd frontend
npm install
npm run deploy
```

No dashboard Cloudflare → **Workers & Pages** → **the-gang** → **Settings** → **Environment variables**:

- `API_ORIGIN` = `https://api-gang.httpslaudo.com.br`

Custom domain: `gang.httpslaudo.com.br` (Pages → Custom domains).

## 2) API (Tunnel — igual hub/loja)

No PC/VPS que vai ficar ligado:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
Copy-Item .env.production.example .env.production
# Edite SECRET_KEY, LIVEKIT_*, CORS_ORIGINS
$env:ENVIRONMENT="production"
# Carregue .env.production nas variáveis ou use um process manager
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Tunnel:

```powershell
cloudflared tunnel create the-gang-api
cloudflared tunnel route dns the-gang-api api-gang.httpslaudo.com.br
# Ajuste deploy/cloudflared.gang.yml.example com o tunnel id
cloudflared tunnel --config caminho\cloudflared.gang.yml run
```

CORS da API deve incluir:

`https://gang.httpslaudo.com.br,https://the-gang.pages.dev`

## 3) `.exe` (Tauri)

Ver `desktop/README.md`. O `.exe` só empacota a UI; a API continua em `api-gang`.

## Modo rápido (PC ligado)

```powershell
cd deploy
.\run-online.ps1
```

Isso sobe a API na porta 8000 + tunnel `*.trycloudflare.com`.  
O front em `https://gang.httpslaudo.com.br` já faz proxy `/api` → esse tunnel.

Login seed: `juninho` / `paraiba123`

**Importante:** o PC precisa ficar ligado com o script aberto. Se reiniciar o tunnel e a URL mudar, atualize `FALLBACK_API_ORIGIN` em `frontend/functions/api/[[path]].js` e rode `npm run deploy`.

## Checklist

- [x] Front Pages em `gang.httpslaudo.com.br`
- [x] Proxy `/api` + `/uploads`
- [ ] Tunnel permanente `api-gang` (recomendado depois)
- [x] LiveKit no `.env.production`
- [ ] Abrir `https://gang.httpslaudo.com.br` e logar
