# Changelog

All notable changes to TokenScope are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-07-02

### Added

- **`// tokens_over_time` chart in the desktop dashboard.** Dependency-free stacked-bar
  SVG per day and per tool (Claude / Codex / Antigravity) with a green daily-cost line
  overlay on its own scale, hover tooltip (per-tool breakdown, total, cost), sparse
  axis labels, missing days filled for ranges ≤ 90d. Theme-aware, collapsible, i18n
  EN/FR, re-renders on tool/range/lang change and window resize. (`desktop/web.py`)
- **Quota alert notifications.** Windows balloon/toast from the tray icon when a Claude
  window reaches ≥ 90% used or a Codex/Spark window drops to ≤ 10% left, with hysteresis
  (re-arms below 85% / above 15%) so a window hovering at the threshold doesn't spam.
  (`desktop/tray.py`)
- **Dynamic tray icon badge.** The tray icon gains a yellow dot at ≥ 75% and a red dot at
  ≥ 90% quota pressure across all monitored windows. (`desktop/icon.py`, `desktop/tray.py`)
- **CSV / JSON export.** Header buttons download the currently loaded summary (per-day,
  per-project, per-model) as `tokenscope_<range>_<date>.csv/json`. (`desktop/web.py`,
  `desktop/tray.py` enables WebView2 downloads)
- **Update check.** The dashboard queries the latest GitHub release (cached 6h) and shows
  a yellow `vX.Y.Z ↗` pill in the header when a newer version exists. (`desktop/web.py`)
- **Sortable project & model tables** — click a column header to cycle desc → asc →
  default order. (`desktop/web.py`)
- **Collapsible tray popup sections.** Claude and Codex (+Spark) groups fold via their
  headers; state persists across opens and the popup window refits. (`desktop/web.py`)

### Changed

- **Claude subscription limit windows are parsed dynamically** (`five_hour` → `5h`,
  `seven_day` → `All`, any `seven_day_<model>` → `<Model> only`), so renamed
  model-specific weekly windows (e.g. the new Fable window) appear without a code
  change; the tray popup renders whatever rows the API returns. (`backend/local_sources.py`,
  `desktop/web.py`)
- Tray popup row labels widened (74 → 86px) so "Weekly (All)" no longer truncates;
  utilization card separators now follow the theme instead of a hardcoded dark color.
  (`desktop/web.py`)

## [1.2.0] - 2026-06-30

### Added

- **Custom Win32 system-tray menu (frameless HTML popup).** The native pystray menu is
  replaced by a self-contained `Win32Tray` icon (`Shell_NotifyIcon`) whose left- *or*
  right-click opens a styled, theme-aware popup at the cursor — Windows never draws a
  native menu. The popup lists the live usage limits (Claude `5h` / `Weekly (All)` /
  `Sonnet only`; Codex `5h` / `Weekly`; `GPT-5.3-Codex-Spark` `5h` / `Weekly`) plus
  *Show TokenScope*, *Start with Windows* and *Quit*. (`desktop/tray.py`, `desktop/web.py`)
- **GPT-5.3-Codex-Spark usage limits** in the Codex utilization card and the tray popup
  (`5h` + `Weekly`), grouped under a labelled header. (`desktop/web.py`, `backend/local_sources.py`)
- **"Start with Windows (minimized)" toggle.** Writes an `HKCU\…\Run` entry that relaunches
  the app with `--minimized` (window starts hidden in the tray). (`desktop/tray.py`)
- **`/tray` route** serving the popup page; `GET /api/theme` without a value now reads the
  current theme non-destructively. (`desktop/server.py`)

### Changed

- **Codex utilization scan window widened 24h → 30d.** Idle or freshly-reset limits (and
  the less-frequently-logged Spark limits) now still display; any window whose reset has
  passed rolls over to 100% left. A 24h window blanked the panel whenever Codex hadn't been
  used in the last day. (`backend/local_sources.py`)
- **Codex card always renders the limit bars**, defaulting to 100% left when a window
  hasn't been observed yet, instead of showing "no codex rate-limit data in recent
  sessions". (`desktop/web.py`)
- **Expired Claude OAuth token keeps the subscription panel populated.** A present-but-expired
  token now stays in `subscription` mode and serves the cached limits rather than falsely
  reporting "not signed in" until Claude Code refreshes the token. (`backend/local_sources.py`)
- **Tray popup placement is DPI- and multi-monitor-aware** — sized and positioned against
  the work area and scale factor of the monitor under the cursor. (`desktop/tray.py`)
- **Dropped the `pystray` dependency**; the tray is now pure Win32. (`desktop/requirements.txt`,
  `desktop/tokenscope-tray.spec`)
- Tray popup shows Claude as `% used` (bar fills as consumed) and Codex/Spark as `% left`,
  matching each tool's dashboard convention. (`desktop/web.py`)

### Fixed

- **Tray popup opens reliably and dismisses on click-away.** Show/position/hide go through
  Win32 (`SetWindowPos`), focus is forced with the `AttachThreadInput` trick, and a Win32
  watcher hides the popup once it loses the foreground — WebView2 does not fire a reliable
  JS `blur`. (`desktop/tray.py`)
- **Right-click on the tray icon works on Windows 11** (`WM_CONTEXTMENU` is handled, not only
  `WM_RBUTTONUP`). (`desktop/tray.py`)
- **Tray icon re-adds itself when the shell restarts** (`TaskbarCreated`). (`desktop/tray.py`)
- The popup no longer shows the native WebView2 context menu on right-click. (`desktop/web.py`)

## [1.1.0] - 2026-06-26

### Added

- **Antigravity (Google Gemini) as a third local source.** Reads token usage from
  the local `~/.gemini/antigravity/conversations/*.db` SQLite "trajectory" databases.
  Each generation's input/output tokens, model name and timestamp are decoded from the
  per-row protobuf blob with a tolerant, schema-free wire reader; the project/workspace
  is recovered from `trajectory_metadata_blob`. Read-only; encrypted `*.pb` files are
  skipped. (`backend/local_sources.py`)
- **Antigravity cost estimation.** Family-based pricing for Gemini (Pro / Flash /
  Flash Lite), Claude and GPT-OSS models against public list rates. Subscription usage
  carries no per-token bill, so these figures are an estimate. (`backend/local_sources.py`)
- **`antigravity` filter tab** in the dashboard. (`desktop/web.py`)
- **Theme persistence.** The dark/light choice is now saved server-side to
  `%LOCALAPPDATA%\TokenScope\theme.json` and exposed via `GET /api/theme`. (`desktop/server.py`)
- **Native title-bar follows the dashboard theme.** The Windows DWM caption/border/text
  colours are repainted to match dark or light, kept in sync by a background loop.
  (`desktop/tray.py`)
- **Single-instance guard.** A named Windows mutex stops a second TokenScope tray
  process from launching. (`desktop/tray.py`)
- **Friendly model names** in the breakdown table — raw API ids such as
  `claude-opus-4-8` render as `Claude Opus 4.8`; already-friendly names pass through,
  with the raw id kept as a tooltip. (`desktop/web.py`)
- **Tests** for Antigravity protobuf decoding, pricing, DB event aggregation and
  graceful degradation when the directories are missing. (`backend/tests/test_local_sources.py`)

### Changed

- `read_local_summary` now also collects Antigravity events when `tool` is `None` or
  `"antigravity"`. (`backend/local_sources.py`)
- The single-purpose `_apply_dark_titlebar` was generalised into `_apply_titlebar_theme(hwnd, theme)`
  plus a reusable `_window_hwnd` helper. (`desktop/tray.py`)
- The utilization section is hidden entirely when no card applies (e.g. the Antigravity
  tab) and the grid collapses to one column with a single card. (`desktop/web.py`)
- `build.bat` escapes the `->` in its echo so the arrow prints correctly. (`desktop/build.bat`)

### Fixed

- Opus pricing detection now accepts both API ids (`opus-4-1`) and Antigravity display
  names (`Opus 4.6`), so 4.5+ Opus is correctly priced at $5/$25 instead of $15/$75.
  (`backend/local_sources.py`)

### Not changed

- **No subscription / live-quota panel for Antigravity.** Only token usage and an
  estimated cost are tracked; the unreliable `cloudcode-pa` quota fetch was not added.
  The utilization cards remain Claude- and Codex-only.
- **Claude and Codex sources** (usage, utilization, pricing) are unchanged.
- **The React + FastAPI web app** (manual import, stored history, thresholds, charts)
  is unchanged; this release only touches the desktop tray app and the shared backend reader.

## [1.0.0] - 2026

Initial release: desktop tray app, FR/EN i18n, themes, de-branded. Local-first token-usage
and subscription tracker for Claude Code and Codex, shipping as a Windows tray app and a
React + FastAPI web app.

[1.2.0]: https://github.com/imnotStealthy/tokenscope/releases/tag/v1.2.0
[1.1.0]: https://github.com/imnotStealthy/tokenscope/releases/tag/v1.1.0
[1.0.0]: https://github.com/imnotStealthy/tokenscope/releases/tag/v1.0.0
