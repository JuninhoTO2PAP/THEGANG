# Desktop — THE GANG (.exe via Tauri v2)

Empacota a mesma UI do PWA numa WebView nativa do Windows. O backend continua separado (API + LiveKit).

## Pré-requisitos

- [Rust](https://rustup.rs/) estável
- Visual Studio Build Tools (C++) no Windows
- Node.js 20+
- Frontend buildável (`frontend/`)

## Bootstrap (primeira vez)

```powershell
cd desktop
npm install
npm create tauri-app@latest . -- --force
```

Quando o assistente perguntar, use:

- app name: `THE GANG`
- identifier: `app.thegang.desktop`
- frontend: existing / Vite
- `devUrl`: `http://localhost:5173`
- `frontendDist`: `../frontend/dist`

Ou copie `tauri.stub.json` para dentro de `src-tauri/tauri.conf.json` e ajuste os caminhos.

## Dev

```powershell
# terminal 1 — API
cd backend
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000

# terminal 2 — Vite
cd frontend
npm run dev

# terminal 3 — janela desktop
cd desktop
npm run tauri dev
```

## Gerar .exe

```powershell
cd frontend
npm run build

cd ..\desktop
npm run tauri build
```

O instalador sai em `desktop/src-tauri/target/release/bundle/` (NSIS/MSI).

## Identidade

| Campo | Valor |
|--------|--------|
| productName | THE GANG |
| identifier | app.thegang.desktop |
| version | 0.1.0 |

## Notas

- LiveKit (voz/vídeo/tela) precisa de `LIVEKIT_*` no `.env` do backend.
- O `.exe` só abre a UI; a API continua no servidor do time.
