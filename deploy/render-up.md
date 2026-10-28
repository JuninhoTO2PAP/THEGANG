# Subir API no Render (sem Railway)

## 1. Conta
https://dashboard.render.com/register (GitHub)

## 2. Repo no GitHub
1. https://github.com/new → nome `the-gang` (pode ser privado)
2. No PowerShell, na pasta do projeto:

```powershell
cd "C:\Users\Carlos Augusto\Desktop\discord do junin\the-gang"
git branch -M main
git remote add origin https://github.com/SEU_USER/the-gang.git
git commit -m "THE GANG API + front para Render"
git push -u origin main
```

## 3. Blueprint
1. Render → **New** → **Blueprint**
2. Conecte o repo `the-gang`
3. Apply → sobe Postgres + `the-gang-api`

## 4. URL no Pages
Copie `https://the-gang-api-xxxx.onrender.com` e:
- Cloudflare Pages → `the-gang` → Settings → Environment variables → `API_ORIGIN` = essa URL  
  **ou** avise aqui que eu atualizo o `FALLBACK_API_ORIGIN` e faço o deploy do front.

Login: `juninho` / `paraiba123`  
(1º acesso free pode demorar ~30s se o serviço estiver “dormindo”)
