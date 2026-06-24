# TokenScope · PRD

## Original problem statement
> Je souhaite créer une app qui permet de visualiser, de savoir combien en est la
> consommation des tokens pour Claude via l'API, Codex, et Antigravity (dont via
> ce logiciel, utilisant les modèles Gemini, soit Claude ou GPT) et de suivre cette
> consommation

## User choices
- Data source: **import CSV / JSON** files (no live API integration)
- Tools tracked: **Claude API, Codex, Antigravity** (no others)
- Auth: **none** (local-first; user feeds data via Claude Code)
- UX: **Dashboard + tables + threshold alerts + floating system tray**
- Budget feature: **NO**

## Architecture
- Backend: FastAPI (`/app/backend/server.py`), MongoDB collections `usage` + `thresholds`
- Frontend: React + Tailwind + Shadcn UI + Recharts, dark "Swiss + Terminal" theme
- All API routes prefixed `/api`; frontend uses `REACT_APP_BACKEND_URL`

## Core endpoints
- `POST /api/usage/import` – CSV/JSON file import (normalises tool/model/timestamp)
- `POST /api/usage` – manual create · `DELETE /api/usage/{id}` · `DELETE /api/usage` (wipe)
- `POST /api/usage/seed` – synthetic demo data (14 days × 9 tool/model combos)
- `GET /api/usage` – list with filters (tool, model, days, limit)
- `GET /api/usage/summary` – aggregated totals, by_tool, by_model, by_underlying_model, by_day
- `GET /api/usage/live` – latest entry (powers the system-tray widget)
- `GET /api/threshold` · `PUT /api/threshold` – daily_tokens & daily_cost_usd thresholds
- `GET /api/pricing` – internal pricing table per 1M tokens

## What's implemented (2026-02)
- File import for CSV + JSON (flexible field naming: prompt_tokens/input_tokens, etc.)
- Cost computation from `underlying_model` when present (correctly prices Antigravity)
- Dashboard: header with 7d/30d/90d range, summary KPI cards, line chart over time
  with red dashed threshold line, cost-by-tool bar chart, per-model breakdown table,
  daily threshold panel with progress bars & breach indicator, recent-entries table
  with delete actions, wipe-all button
- Floating "system tray" widget (terminal style) – live model, tool, last entry,
  today_tokens / today_cost vs threshold; minimize / reopen control (positioned to
  not collide with the Emergent badge)
- Sonner toasts for import / save / wipe feedback
- All interactive elements carry `data-testid`

## Testing
- Backend: 16/16 pytest tests pass (`/app/backend/tests/test_tokenscope_api.py`)
- Frontend: dashboard + tray + threshold breach + CSV upload verified via Playwright

## Backlog / Next actions
- **P1** Per-tool / per-model filters on the charts and tables
- **P1** Export aggregated summary as CSV/JSON
- **P2** Direct connectors (Anthropic, OpenAI, Vertex usage APIs) instead of file import
- **P2** Per-day breakdown drilldown view (click a day → list entries of that day)
- **P3** Editable pricing table from the UI
- **P3** Multi-user (auth) and shared workspaces
