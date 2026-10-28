# Render — API THE GANG (alternativa ao Railway)

Railway pausou **novos cadastros** após o incidente de 21/out — por isso o login falha.

## Passo a passo (≈10 min)

1. Crie conta em https://dashboard.render.com/register (GitHub ok).
2. Suba o projeto no GitHub (repo privado ok) **ou** use “Deploy an existing image” / Blueprint.
3. **New → Blueprint** → selecione o repo `the-gang` (precisa do `render.yaml` na raiz).
4. Preencha as env que pedirem sync:
   - `LIVEKIT_URL` = `wss://the-gang-project-ifijvidj.livekit.cloud`
   - `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` (as do `.env.production`)
5. Deploy → anote a URL `https://the-gang-api-xxxx.onrender.com`
6. No Cloudflare Pages (projeto `the-gang`):
   - Variable `API_ORIGIN` = essa URL (sem `/` no final)
7. Ou edite `FALLBACK_API_ORIGIN` em `frontend/functions/api/[[path]].js` e redeploy.

Login demo após seed: `juninho` / `paraiba123`

> Free tier: o serviço “dorme” ~15 min sem tráfego; o 1º request pode demorar ~30s.
