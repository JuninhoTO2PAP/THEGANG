# Railway — API THE GANG

## Um comando (depois do login)

```powershell
cd backend
npx @railway/cli login
npx @railway/cli init
npx @railway/cli add --database postgres
npx @railway/cli up
npx @railway/cli domain
```

Variáveis necessárias (Settings → Variables):

```
ENVIRONMENT=production
SECRET_KEY=<gere uma chave longa>
CORS_ORIGINS=https://gang.httpslaudo.com.br,https://the-gang.pages.dev
SEED_ON_BOOT=1
LIVEKIT_URL=wss://the-gang-project-ifijvidj.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

`DATABASE_URL` vem automático do plugin Postgres.

Depois: atualize `FALLBACK_API_ORIGIN` / `API_ORIGIN` do Pages para a URL `*.up.railway.app`.
