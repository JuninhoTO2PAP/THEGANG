# THE GANG

Mini Discord privado de um time de Free Fire. Acesso só por convite. Esta entrega é a **Etapa 1**: estrutura do repositório, banco e autenticação. Chat em tempo real, PWA e o `.exe` vêm nas etapas seguintes.

## Arquitetura

```text
the-gang/
├── backend/     FastAPI, SQLite agora, PostgreSQL em produção
├── frontend/    PWA (Vite + HTML/CSS/JS) — próxima etapa de interface
├── desktop/     Tauri v2 — stub da Fase 3
└── docker-compose.yml
```

O browser (ou o futuro app instalado) fala com a API por HTTPS. Mensagens em tempo real usarão WebSocket. Voz e tela, na Fase 3, passam por um servidor LiveKit — não pelo SQLite.

```text
PWA / Tauri  --HTTPS-->  FastAPI  --SQL-->  SQLite (dev) / PostgreSQL (prod)
                \--WSS-->  /api/ws   (próxima etapa)
                \--WebRTC--> LiveKit  (Fase 3)
```

## Stack

| Camada | Escolha |
| --- | --- |
| API | Python 3.11+, FastAPI, WebSocket nativo |
| Dados | SQLAlchemy 2, Pydantic v2, Alembic, SQLite → PostgreSQL |
| Sessão | JWT (access 15 min + refresh de 7 dias, rotação e revogação) |
| Senha | bcrypt, custo 12, via passlib |
| Limite de login | slowapi, 5 tentativas por minuto por IP |
| Front | HTML, CSS e JavaScript puro, Vite, Workbox (ainda não gerado) |
| Desktop | Tauri v2 (stub) |
| Voz | LiveKit (rotas reservadas, resposta 501) |

SQLAlchemy 2 + Pydantic v2, sem SQLModel: a migração e os schemas ficam explícitos.

## Fases do produto

| Fase | O que entra | Situação |
| --- | --- | --- |
| 1 | Convite, login, perfil, canais, chat, DM, upload, PWA | Auth e banco prontos. Chat e PWA nas próximas etapas |
| 2 | Push, grupos privados, menções, busca | Tabela `push_subscriptions` e rota 501 |
| 3 | Voz, tela, `.exe` Tauri | Rota `/api/voice/token` 501 e `desktop/README.md` |
| 4 | Ranking, agenda de treinos, estatísticas | Só evolução futura, sem código |

## O que a Etapa 1 já faz

- Cadastro só com convite de uso único
- Login por e-mail ou usuário, logout e refresh com rotação
- Reuso de um refresh já gasto derruba as sessões daquele membro
- Admin gera e lista convites
- Quem entra por convite já cai nos canais públicos (`geral`, `treinos`)
- Seed de desenvolvimento com o time de teste
- `GET /api/health`

Presença online (`is_online`) fica para o WebSocket. O login atualiza `last_seen`, mas não marca a pessoa como online — senão ela pareceria online depois de fechar a aba.

O access token continua válido até expirar (15 minutos) mesmo depois do logout. O logout revoga o refresh, que é o que renovaria a sessão. É o comportamento normal de JWT curto.

## Pré-requisitos

- Python 3.11 ou mais novo (3.14 também funciona)
- PowerShell (os comandos abaixo são os do Windows)
- Docker Desktop, se for usar o compose

No Windows, o atalho `python` da Microsoft Store às vezes não aponta para o interpretador instalado. Prefira o launcher `py` ou o caminho completo do `python.exe`.

## Subir a API

Na pasta `backend`:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Documentação interativa: http://127.0.0.1:8000/docs
- Saúde: http://127.0.0.1:8000/api/health

Se `py` não existir, use o `python.exe` real (por exemplo o do instalador oficial) no lugar de `py -m venv`.

Docker, a partir da raiz `the-gang`:

```powershell
docker compose up --build
```

O compose sobe só o backend. O serviço do frontend entra quando a interface existir. O primeiro boot demora um pouco: o seed gera o hash bcrypt.

## Variáveis de ambiente

Arquivo: `backend/.env.example`. Segredos nunca vão para o git.

| Variável | Função |
| --- | --- |
| `SECRET_KEY` | Assina o JWT. Troque antes de qualquer servidor público |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Vida do access token (padrão 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Vida do refresh (padrão 7) |
| `BCRYPT_ROUNDS` | Custo do hash, mínimo 12 |
| `DATABASE_URL` | `sqlite:///./thegang.db` no dev |
| `CORS_ORIGINS` | Origens do frontend, separadas por vírgula |
| `SEED_PASSWORD` | Senha das contas de demonstração |
| `ENVIRONMENT` | `development`, `test` ou `production` |

Em `production` a API recusa três coisas: `SECRET_KEY` de exemplo, SQLite e origem `http://`. HTTPS é obrigatório no ar por causa do PWA e, depois, do WebRTC.

Chaves de VAPID e LiveKit já estão no exemplo, vazias. Ainda não são lidas.

PostgreSQL, quando for a hora:

```text
DATABASE_URL=postgresql+psycopg://thegang:senha@host:5432/thegang
pip install "psycopg[binary]"
alembic upgrade head
```

## Conta do seed

Só existe o administrador. Novos membros entram **apenas com convite** gerado por ele em **Configurações → Convites**.

| Usuário | Senha | Papel |
| --- | --- | --- |
| `juninho` | `paraiba123` | administrador |

Canais criados: `geral` e `treinos`. Nenhum convite vem pré-criado.

Para zerar o banco e recriar só essa conta:

```powershell
cd backend
python -m app.db.reset
```

O seed/reset não rodam com `ENVIRONMENT=production`.

## Testar o auth

Com a API no ar:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType "application/json" `
  -Body '{"login":"juninho","password":"paraiba123"}'

$login.tokens.access_token
```

No Swagger (`/docs`), clique em Authorize e cole só o access token. Gere um convite em `POST /api/auth/invites` (admin) e use o código no cadastro.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/register `
  -ContentType "application/json" `
  -Body '{"invite_code":"GANG-XXXXXXXX","username":"player1","email":"player1@example.com","password":"SenhaForte1","nickname":"Player"}'
```

Rotas desta etapa:

| Método | Caminho | Quem |
| --- | --- | --- |
| POST | `/api/auth/register` | público, 5/minuto |
| POST | `/api/auth/login` | público, 5/minuto |
| POST | `/api/auth/refresh` | quem tem refresh |
| POST | `/api/auth/logout` | quem tem refresh |
| GET | `/api/auth/me` | access token |
| POST | `/api/auth/invites` | admin |
| GET | `/api/auth/invites` | admin |

Testes automáticos, na pasta `backend` com o venv ativo:

```powershell
pytest
ruff check app tests alembic
```

## Deploy

Domínio ainda não definido. Troque os placeholders abaixo pelo endereço real do time.

| Peça | Sugestão | URL de exemplo |
| --- | --- | --- |
| API | Render, Railway ou Fly.io | `https://api.SEU_DOMINIO` |
| PWA | Vercel ou Netlify | `https://SEU_DOMINIO` |
| Voz (Fase 3) | LiveKit Cloud ou LiveKit no Fly.io | `wss://livekit.SEU_DOMINIO` |

Render (API):

1. Repositório com raiz em `the-gang` (ou informe a pasta `backend` como root).
2. Runtime Python 3.11. Comando de build: `pip install -r requirements.txt` e `pip install "psycopg[binary]"`.
3. Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Não rode o seed de demonstração no serviço público.
5. Variáveis: `ENVIRONMENT=production`, `SECRET_KEY` longa, `DATABASE_URL` do Postgres do Render, `CORS_ORIGINS=https://SEU_DOMINIO`.
6. Disco persistente não serve para SQLite no Render free (o disco some). Use Postgres.

Fly.io segue a mesma ideia: `fly.toml` apontando para `backend/Dockerfile`, Postgres via `fly postgres`, segredos com `fly secrets set SECRET_KEY=...`.

Vercel (quando o frontend existir): importe a pasta `frontend`, framework Vite, e aponte a variável da URL da API para `https://api.SEU_DOMINIO`. O service worker e o manifest exigem HTTPS. `localhost` continua liberado para desenvolvimento.

## Fase 3 (ainda não implementar)

- LiveKit: `POST /api/voice/token` responde 501. Na hora, o backend emite um token de sala e o browser entra com o SDK JS. Compartilhar tela é uma track de screen share da mesma sala.
- Tauri: passos em `desktop/README.md`. O `.exe` abre a mesma UI; a API continua no servidor.

## Próxima etapa

Chat: canais, histórico paginado, WebSocket, indicador de digitação e recibo simples de entrega/leitura. O banco dessas tabelas já foi criado nesta etapa.
