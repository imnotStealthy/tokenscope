<p align="center">
  <img src="assets/tokenscope-logo.png" alt="TokenScope logo" width="140" />
</p>

<h1 align="center">TokenScope</h1>

<p align="center"><strong>Local-first token-usage &amp; subscription tracker for Claude Code and Codex.</strong></p>

TokenScope reads your own local session files and shows — per project, per model,
over any time range — how many tokens you've spent, the estimated cost, and how much
of your **subscription quota** (Claude 5h / weekly, Codex 5h / weekly / spark / credits)
is left. It runs entirely on your machine: no cloud collector, no telemetry.

It ships in two forms:

- a standalone **Windows tray app** (`TokenScope.exe`) — a native, black-OLED dashboard
  window with a system-tray icon, zero dependencies to install;
- the original **React + FastAPI web app** — same data plus manual import (CSV/JSON),
  stored history, daily thresholds and charts.

---

## Features

- **Usage by project** — tokens & cost grouped by the working directory of each session.
- **Breakdown by model** — input / output / total / calls / cost per model.
- **Cost estimation** — priced per model against the official Anthropic & OpenAI rates
  (cache reads at 0.1×; Codex output already includes reasoning — not double-counted).
- **Subscription utilization** — Claude (5h / weekly / Sonnet) read from the Anthropic
  OAuth usage API; Codex (5h / weekly / spark / credits) read from rollout rate-limits,
  shown as **remaining %** (100 % = full, 0 % = exhausted).
- **API vs subscription detection** — auto-labels Claude as `subscription` or `api`
  (Claude Platform / pay-as-you-go) and tracks a daily / monthly **budget** in either mode.
- **Time ranges** — `24h · 7d · 30d · 90d · LIFE` (lifetime = every session since you
  started using Claude Code / Codex). Lifetime is pre-warmed in the background.
- **All / Claude / Codex** filter and collapsible sections.
- **FR / EN** language toggle (English default; preference persisted).
- Real-time refresh; live clock and quota count-downs.

---

## Architecture

| Surface | Stack | Role |
| --- | --- | --- |
| `desktop/` | Python stdlib HTTP + pywebview + pystray, packaged with PyInstaller | The standalone tray `.exe` — native window, embedded dashboard, local-only |
| `frontend/` | React 19 (CRA + craco), Tailwind, Recharts | Full web UI: live local view + stored history, import, thresholds, charts |
| `backend/` | FastAPI + MongoDB (motor) | REST API for the web app; serves both stored and local data |
| `backend/local_sources.py` | pure Python (shared) | The reader: parses `~/.claude` & `~/.codex` sessions, prices them, and fetches subscription utilization. Used by **both** the backend and the tray app |

**Data sources** (read-only, on your machine):
`~/.claude/projects/**/*.jsonl`, `~/.claude/.credentials.json` (OAuth token),
`~/.codex/sessions/**/rollout-*.jsonl`, and the cache at `~/.claude-rpc`.
The **only** outbound network call is the optional Anthropic OAuth *usage* read.

---

## Quick start

### 1. Tray app (recommended — no install)

```text
bin\TokenScope.exe
```

Double-click it:

- opens as a **native application window** (not a browser tab);
- a tray icon appears (tooltip shows live `C 5h %` / `X 5h %`);
- **closing the window** hides it to the tray → right-click the tray to **Show / Quit**.

Binds to `127.0.0.1` only; falls back to the default browser on the rare host without
the WebView2 runtime. See [`desktop/README.md`](desktop/README.md) for details and to
build it yourself (`cd desktop && build.bat`).

### 2. Web app (dev)

```bash
# backend  (needs a running MongoDB; set MONGO_URL & DB_NAME)
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# frontend
cd frontend
yarn install        # or: npm install
yarn start          # or: npm start  -> http://localhost:3000
```

Use the **local** source toggle for live `~/.claude` / `~/.codex` data, or **stored**
for imported history.

---

## Configuration

Backend environment variables:

| Var | Default | Purpose |
| --- | --- | --- |
| `MONGO_URL` | — (*required*) | MongoDB connection string |
| `DB_NAME` | — (*required*) | Database name |
| `TOKENSCOPE_API_KEY` | *empty* | If set, write/mutating endpoints require `X-API-Key` |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins (pin this if deployed) |
| `MAX_UPLOAD_BYTES` / `MAX_IMPORT_ROWS` | 5 MB / 50 000 | Import limits |

Reader toggles (used by the tray app and backend):

| Var | Purpose |
| --- | --- |
| `TOKENSCOPE_DIR` | Override the cache dir (default `~/.tokenscope`) |
| `TOKENSCOPE_CLAUDE_OAUTH=0` | Disable the OAuth usage call (use cached limits only) |

---

## Privacy & security

- **Local-first.** All parsing happens on your machine; the desktop server binds to
  `127.0.0.1` and exposes only read-only endpoints.
- **No secret leakage.** OAuth tokens / API keys are never logged, returned in API
  responses, or persisted in plaintext beyond their original credential file. Status
  responses expose only boolean availability flags and percentages.
- **No telemetry.** Nothing is sent anywhere except the optional official Anthropic
  usage read.

A 5-dimension security audit (secrets, XSS, network/SSRF/TLS, file I/O, code execution)
found **no exploitable vulnerabilities** under this threat model.

---

## Project layout

```text
backend/      FastAPI server + local_sources.py (the shared reader) + tests/
frontend/     React web app (src/lib/i18n.js holds the FR/EN dictionary)
desktop/      Tray .exe sources: tray.py, server.py, web.py, icon.py, build.bat
bin/          Prebuilt TokenScope.exe
```

## Roadmap

- **Antigravity (Google)** usage — will appear automatically once added to
  `backend/local_sources.py`; the UI already accounts for additional tools.
