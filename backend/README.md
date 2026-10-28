# Backend — THE GANG

API FastAPI da Etapa 1 (auth, banco, seed). O panorama do produto está no [README da raiz](../README.md).

## Rodar

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Testes e lint:

```powershell
pytest
ruff check app tests alembic
```

## Pastas

| Pasta | Papel |
| --- | --- |
| `app/core` | Config, JWT, bcrypt, limite de tentativas |
| `app/models` | Tabelas |
| `app/schemas` | Contratos Pydantic |
| `app/api` | Rotas. Chat, upload e WebSocket ainda estão vazios de propósito |
| `app/services` | Regras de cadastro e sessão |
| `app/db` | Engine, seed |
| `alembic` | Migrações |
| `uploads` | Arquivos da próxima etapa (não versionar o conteúdo) |

`GET /api/health` devolve `etapa-1-auth` enquanto o chat não entra.

Única conta do seed: `juninho` / `paraiba123` (admin). Convites são gerados no painel.

```powershell
python -m app.db.reset
```
