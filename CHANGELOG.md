# Changelog

All notable changes to TokenScope are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.0]: https://github.com/imnotStealthy/tokenscope/releases/tag/v1.1.0
[1.0.0]: https://github.com/imnotStealthy/tokenscope/releases/tag/v1.0.0
