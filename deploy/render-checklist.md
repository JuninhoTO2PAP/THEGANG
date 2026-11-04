# Render — criar do zero (checklist)

## 1) Postgres
1. Dashboard → projeto **thegang** → **+ New** → **Postgres**
2. Name: `the-gang-db`
3. Database: `thegang` / User: `thegang`
4. Region: a mesma que for usar na API (ex. Oregon)
5. Plan: **Free**
6. **Create Database**
7. Espera ficar Available

## 2) Web Service
1. **+ New** → **Web Service**
2. Connect GitHub → repo **JuninhoTO2PAP/THEGANG**
3. Settings:
   - Name: `the-gang-api`
   - Language/Runtime: **Docker**
   - Root Directory: `backend`
   - Dockerfile Path: `./Dockerfile` (ou deixe default)
   - Branch: `main`
   - Instance: **Free**
4. **Environment** (antes de Create):

| Key | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `SEED_ON_BOOT` | `1` |
| `CORS_ORIGINS` | `https://gang.httpslaudo.com.br,https://the-gang.pages.dev` |
| `SECRET_KEY` | (Generate: qualquer 40+ chars) |
| `DATABASE_URL` | **Add from Database** → `the-gang-db` → Internal URL |
| `LIVEKIT_URL` | `wss://the-gang-project-ifijvidj.livekit.cloud` |
| `LIVEKIT_API_KEY` | `APIHqq8vYgdewdA` |
| `LIVEKIT_API_SECRET` | `ok0D8xNQNnq0fiIlL1CUdinVRvn1z4CWPTyISZNogqE` |
| `BCRYPT_ROUNDS` | `12` |
| `VAPID_CONTACT` | `mailto:admin@httpslaudo.com.br` |

5. Health Check Path: `/api/health`
6. **Create Web Service** → espera **Live**
7. Copia a URL `https://the-gang-api-xxxx.onrender.com` e manda no chat
