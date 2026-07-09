"""
local_sources.py — Read token usage and subscription utilization directly from
the LOCAL Claude Code and Codex (OpenAI) data on this machine.

Ported from the claude-rpc / codex-rpc reference apps:
  - Claude tokens come from ~/.claude/projects/<encoded>/<session>.jsonl assistant
    lines (message.usage). Project = the line's `cwd`.
  - Claude subscription utilization (5h / All / Sonnet) comes from the Anthropic
    OAuth usage API, with ~/.claude-rpc/limits-cache.json as a fallback.
  - Codex tokens come from ~/.codex/sessions/**/rollout-*.jsonl token_count events
    (info.last_token_usage). Project = session_meta.payload.cwd, model = the most
    recent turn_context.payload.model.
  - Codex utilization (5h primary / weekly secondary / Spark / credits) comes from
    the same rollouts' rate_limits, plus plan_type from ~/.codex/auth.json.

Everything is read-only. Secrets (OAuth tokens, API keys) are never logged.
Degrades gracefully (returns available=False) when a data dir is missing, so the
backend still boots on hosts without local Claude/Codex installs.
"""
from __future__ import annotations

import glob
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ----- paths -----
def _home() -> Path:
    return Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".")


def claude_dir() -> Path:
    return Path(os.environ.get("TOKENSCOPE_CLAUDE_DIR") or (_home() / ".claude"))


def codex_dir() -> Path:
    return Path(os.environ.get("TOKENSCOPE_CODEX_DIR") or (_home() / ".codex"))


def claude_rpc_dir() -> Path:
    return Path(os.environ.get("TOKENSCOPE_CLAUDE_RPC_DIR") or (_home() / ".claude-rpc"))


def tokenscope_dir() -> Path:
    return Path(os.environ.get("TOKENSCOPE_DIR") or (_home() / ".tokenscope"))


# ----- pricing (USD per 1M tokens), family-based for robustness to model id variants -----
# Aligned with backend PRICING for Claude/OpenAI; cache multipliers from the reference apps.
CLAUDE_CACHE_READ_MULT = 0.1
CLAUDE_CACHE_WRITE_5M_MULT = 1.25
CLAUDE_CACHE_WRITE_1H_MULT = 2.0
CODEX_CACHED_INPUT_MULT = 0.1  # OpenAI bills cached input at 0.1x; no cache-write cost


def claude_pricing(model_id: str) -> Tuple[str, float, float]:
    """Return (family_label, input_rate, output_rate) per 1M tokens for a Claude model.

    Rates verified against the official Anthropic pricing page (USD per MTok):
      Fable/Mythos 5  10 / 50
      Opus 4.5–4.8     5 / 25   (Opus 4 & 4.1 are the deprecated 15 / 75 tier)
      Sonnet 4.x       3 / 15
      Haiku 4.5        1 / 5    (Haiku 3.5 = 0.8 / 4)
    Cache: read 0.1x, 5m-write 1.25x, 1h-write 2x of the input rate.
    """
    b = (model_id or "").lower().split("[")[0]
    if "fable" in b or "mythos" in b:
        return ("Fable", 10.0, 50.0)
    if "haiku" in b:
        if "haiku-3" in b:
            return ("Haiku", 0.8, 4.0)
        return ("Haiku", 1.0, 5.0)
    if "sonnet" in b:
        return ("Sonnet", 3.0, 15.0)
    if "opus" in b:
        # Only the deprecated Opus 4 (bare) and Opus 4.1 are $15/$75; 4.5+ are $5/$25.
        # Accept API ids (opus-4-1) and Antigravity display names (Opus 4.6).
        m = re.search(r"opus[ \-]?4(?:[.\-](\d+))?", b)
        if m and m.group(1) in (None, "1"):
            return ("Opus 4.1", 15.0, 75.0)
        return ("Opus", 5.0, 25.0)
    return (model_id or "unknown", 0.0, 0.0)


def codex_pricing(model_id: str) -> Tuple[str, float, float]:
    """Return (family_label, input_rate, output_rate) per 1M tokens for an OpenAI/Codex model."""
    b = (model_id or "").lower()
    if re.search(r"gpt[ .-]?5[ .-]?6", b):
        if "luna" in b:
            return ("GPT-5.6 Luna", 1.0, 6.0)
        if "terra" in b:
            return ("GPT-5.6 Terra", 2.50, 15.0)
        if "sol" in b:
            return ("GPT-5.6 Sol", 5.0, 30.0)
    if "codex" in b:
        return ("Codex", 1.75, 14.0)
    if "gpt-5.5" in b or "gpt-5-5" in b:
        return ("GPT-5.5", 5.0, 30.0)
    if "nano" in b:
        return ("Nano", 0.20, 1.25)
    if "mini" in b:
        return ("Mini", 0.75, 4.50)
    if "gpt-5.4" in b or "gpt-5-4" in b:
        return ("GPT-5.4", 2.50, 15.0)
    if "gpt-5.2" in b or "gpt-5-2" in b:
        return ("GPT-5.2", 1.25, 10.0)
    if "gpt-4o" in b:
        return ("GPT-4o", 2.50, 10.0)
    return (model_id or "unknown", 0.0, 0.0)


# ----- helpers -----
def _norm_path(p: str) -> str:
    return (p or "").replace("\\", "/").rstrip("/").lower()


def _basename(p: str) -> str:
    segs = [s for s in (p or "").replace("\\", "/").split("/") if s]
    return segs[-1] if segs else (p or "")


def _parse_ts(raw) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _epoch_secs_to_iso(secs) -> Optional[str]:
    try:
        return datetime.fromtimestamp(float(secs), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def _reset_to_iso(v) -> Optional[str]:
    """Normalize a reset value to an ISO string. Already-ISO strings pass through;
    numeric epoch values are converted (seconds vs milliseconds by magnitude)."""
    if v is None:
        return None
    if isinstance(v, str):
        try:
            v = float(v)  # purely numeric string -> epoch below
        except ValueError:
            return v  # non-numeric string assumed already ISO
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(n):
        return None
    if n > 1e11:  # epoch ms (~1.7e12) vs s (~1.7e9)
        n /= 1000.0
    return _epoch_secs_to_iso(n)


def _safe_int(v) -> int:
    """Coerce a token count to a non-negative finite int (rejects inf/NaN/garbage)."""
    try:
        f = float(v or 0)
    except (ValueError, TypeError):
        return 0
    if not math.isfinite(f):
        return 0
    return max(0, min(int(f), 10**12))


def _safe_cost(v) -> float:
    try:
        f = float(v or 0.0)
    except (ValueError, TypeError):
        return 0.0
    if not math.isfinite(f):
        return 0.0
    return round(max(0.0, f), 6)


# per-file parse cache: path -> (mtime, [events])
_FILE_CACHE: Dict[str, Tuple[float, List[dict]]] = {}


def _make_event(tool, model, cwd, ts: Optional[datetime], inp, out, cread, ccreate, cost) -> dict:
    proj = _norm_path(cwd) if cwd else "unassigned"
    # LOCAL day, consistent with the hourly buckets (aggregate) and the dashboard's
    # "today"/chart gap-fill — a UTC day key put evening usage on the next day's bar.
    day = ts.astimezone().strftime("%Y-%m-%d") if ts else ""
    return {
        "tool": tool,
        "model": model or "unknown",
        "project": proj,
        "project_name": _basename(cwd) if cwd else "unassigned",
        "input_tokens": _safe_int(inp),
        "output_tokens": _safe_int(out),
        "cache_read_tokens": _safe_int(cread),
        "cache_creation_tokens": _safe_int(ccreate),
        "cost_usd": _safe_cost(cost),
        "timestamp": ts.astimezone(timezone.utc).isoformat() if ts else None,
        "day": day,
    }


# ----- Claude: token events from session transcripts -----
def _parse_claude_file(path: str) -> List[dict]:
    events: List[dict] = []
    file_cwd: Optional[str] = None
    seen_msgs: set = set()  # Claude Code repeats message.usage on every content-block line
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if not isinstance(o, dict):
                    continue
                cwd = o.get("cwd")
                if isinstance(cwd, str) and cwd:
                    file_cwd = cwd
                if o.get("type") != "assistant":
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                msg_id = msg.get("id")
                dk = f"{msg_id}\x00{o.get('requestId')}" if msg_id else None
                if dk is not None:
                    if dk in seen_msgs:
                        continue
                    seen_msgs.add(dk)
                model = msg.get("model")
                inp = usage.get("input_tokens", 0) or 0
                out = usage.get("output_tokens", 0) or 0
                cread = usage.get("cache_read_input_tokens", 0) or 0
                ccreate = usage.get("cache_creation_input_tokens", 0) or 0
                cc = usage.get("cache_creation") or {}
                w5 = cc.get("ephemeral_5m_input_tokens", 0) or 0
                w1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
                if (w5 + w1) == 0:
                    w5, w1 = ccreate, 0
                if inp == 0 and out == 0 and cread == 0 and ccreate == 0:
                    continue  # synthetic / empty assistant turn carries no usage
                _label, in_rate, out_rate = claude_pricing(model)
                cost = (
                    inp / 1e6 * in_rate
                    + out / 1e6 * out_rate
                    + (
                        cread * CLAUDE_CACHE_READ_MULT
                        + w5 * CLAUDE_CACHE_WRITE_5M_MULT
                        + w1 * CLAUDE_CACHE_WRITE_1H_MULT
                    )
                    / 1e6
                    * in_rate
                )
                ts = _parse_ts(o.get("timestamp"))
                ev = _make_event("claude_api", model, cwd or file_cwd, ts, inp, out, cread, ccreate, cost)
                if dk is not None:
                    ev["dk"] = dk  # resumed sessions replay messages into new files: dedup across files
                events.append(ev)
    except (OSError, ValueError, OverflowError):
        return []
    return events


# ----- Codex: token events from rollout transcripts -----
def _read_codex_config_model() -> Optional[str]:
    cfg = codex_dir() / "config.toml"
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # tiny TOML scan for top-level `model = "..."` (avoids a tomllib dependency / py3.10 gap)
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("["):  # entered a table; stop scanning top-level keys
            break
        if re.match(r"^model\s*=", s):  # exact key: `model_provider = ...` must not match
            val = s.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                return val
    return None


def _parse_codex_file(path: str, default_model: Optional[str]) -> List[dict]:
    events: List[dict] = []
    cwd: Optional[str] = None
    current_model: Optional[str] = default_model
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if not isinstance(o, dict):
                    continue
                t = o.get("type")
                payload = o.get("payload") if isinstance(o.get("payload"), dict) else {}
                if t == "session_meta":
                    c = payload.get("cwd")
                    if isinstance(c, str) and c:
                        cwd = c[4:] if c.startswith("\\\\?\\") else c
                elif t == "turn_context":
                    c = payload.get("cwd")
                    if isinstance(c, str) and c:
                        cwd = c[4:] if c.startswith("\\\\?\\") else c
                    m = payload.get("model")
                    if isinstance(m, str) and m:
                        current_model = m
                elif t == "event_msg" and payload.get("type") == "token_count":
                    info = payload.get("info") or {}
                    delta = info.get("last_token_usage")
                    if not isinstance(delta, dict):
                        continue
                    inp = delta.get("input_tokens", 0) or 0
                    out = delta.get("output_tokens", 0) or 0
                    cached = min(delta.get("cached_input_tokens", 0) or 0, inp)
                    if inp == 0 and out == 0:
                        continue
                    _label, in_rate, out_rate = codex_pricing(current_model or "")
                    uncached = max(0, inp - cached)
                    # output_tokens already INCLUDES reasoning_output_tokens (a sub-breakdown);
                    # verified on real rollouts: total_tokens == input_tokens + output_tokens.
                    cost = (
                        (uncached * in_rate + cached * in_rate * CODEX_CACHED_INPUT_MULT) / 1e6
                        + out * out_rate / 1e6
                    )
                    ts = _parse_ts(o.get("timestamp"))
                    # headline input = fresh (uncached) tokens, consistent with Claude;
                    # cached re-reads are tracked separately in cache_read_tokens.
                    events.append(
                        _make_event("codex", current_model, cwd, ts, uncached, out, cached, 0, cost)
                    )
    except (OSError, ValueError, OverflowError):
        return []
    return events


def _collect_events(root: Path, pattern: str, parser, cutoff_ts: float, *parser_args) -> List[dict]:
    """Walk `root` for files matching `pattern`, parse via `parser` (mtime-cached),
    skipping files whose mtime is older than cutoff_ts."""
    if not root.exists():
        return []
    out: List[dict] = []
    seen = set()
    for fp in glob.iglob(str(root / pattern), recursive=True):
        try:
            mt = os.path.getmtime(fp)
        except OSError:
            continue
        seen.add(fp)
        if cutoff_ts and mt < cutoff_ts:
            continue
        cached = _FILE_CACHE.get(fp)
        if cached and cached[0] == mt:
            events = cached[1]
        else:
            events = parser(fp, *parser_args)
            _FILE_CACHE[fp] = (mt, events)
        out.extend(events)
    # Prune cache entries for files under this root that vanished (rotated/deleted),
    # scoped by path prefix so the other source's entries are untouched.
    root_key = os.path.normcase(str(root))
    for k in [k for k in _FILE_CACHE if os.path.normcase(k).startswith(root_key) and k not in seen]:
        _FILE_CACHE.pop(k, None)
    return out


# One extra day of slack so the mtime prefilter can never exclude an in-window event
# that the authoritative per-event UTC filter in aggregate() would keep (clock/mtime skew).
_MTIME_MARGIN_S = 86400


def read_claude_events(days: int) -> List[dict]:
    cutoff_ts = time.time() - days * 86400 - _MTIME_MARGIN_S
    events = _collect_events(claude_dir() / "projects", "**/*.jsonl", _parse_claude_file, cutoff_ts)
    # Resumed sessions replay old messages into new transcript files with identical
    # usage: keep the first occurrence of each (message.id, requestId) across files.
    seen: set = set()
    out: List[dict] = []
    for ev in events:
        dk = ev.get("dk")
        if dk is not None:
            if dk in seen:
                continue
            seen.add(dk)
        out.append(ev)
    return out


def read_codex_events(days: int) -> List[dict]:
    cutoff_ts = time.time() - days * 86400 - _MTIME_MARGIN_S
    default_model = _read_codex_config_model()
    return _collect_events(
        codex_dir() / "sessions", "**/rollout-*.jsonl", _parse_codex_file, cutoff_ts, default_model
    )


# ----- aggregation (same shape as backend get_summary, plus by_project + cache fields) -----
def aggregate(events: List[dict], days: int, tool: Optional[str] = None) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total_in = total_out = total_cread = total_ccreate = 0
    total_cost = 0.0
    by_tool: Dict[str, dict] = {}
    by_model: Dict[str, dict] = {}
    by_project: Dict[str, dict] = {}
    by_day: Dict[str, dict] = {}
    by_hour: Dict[str, dict] = {}
    want_hours = days <= 2  # hourly buckets only matter for the 24h view
    kept = 0

    for e in events:
        if tool and e["tool"] != tool:
            continue
        ts = _parse_ts(e.get("timestamp"))
        if ts is not None and ts < since:
            continue
        kept += 1
        inp, out = e["input_tokens"], e["output_tokens"]
        cread, ccreate = e["cache_read_tokens"], e["cache_creation_tokens"]
        cost = e["cost_usd"]
        total_in += inp
        total_out += out
        total_cread += cread
        total_ccreate += ccreate
        total_cost += cost

        t, m, proj = e["tool"], e["model"], e["project"]

        bt = by_tool.setdefault(t, {"tool": t, "input_tokens": 0, "output_tokens": 0,
                                    "cache_read_tokens": 0, "cost_usd": 0.0, "entries": 0})
        bt["input_tokens"] += inp
        bt["output_tokens"] += out
        bt["cache_read_tokens"] += cread
        bt["cost_usd"] += cost
        bt["entries"] += 1

        mk = f"{t}::{m}"
        bm = by_model.setdefault(mk, {"tool": t, "model": m, "underlying_model": None,
                                      "input_tokens": 0, "output_tokens": 0,
                                      "cache_read_tokens": 0, "cost_usd": 0.0, "entries": 0})
        bm["input_tokens"] += inp
        bm["output_tokens"] += out
        bm["cache_read_tokens"] += cread
        bm["cost_usd"] += cost
        bm["entries"] += 1

        bp = by_project.setdefault(proj, {"project": proj, "project_name": e["project_name"],
                                          "input_tokens": 0, "output_tokens": 0,
                                          "cache_read_tokens": 0, "cost_usd": 0.0, "entries": 0,
                                          "tools": {}})
        bp["input_tokens"] += inp
        bp["output_tokens"] += out
        bp["cache_read_tokens"] += cread
        bp["cost_usd"] += cost
        bp["entries"] += 1
        bp["tools"][t] = bp["tools"].get(t, 0) + inp + out

        day = e.get("day") or ""
        bd = by_day.setdefault(day, {"day": day, "input_tokens": 0, "output_tokens": 0,
                                     "cost_usd": 0.0, "claude_api": 0, "codex": 0, "antigravity": 0})
        bd["input_tokens"] += inp
        bd["output_tokens"] += out
        bd["cost_usd"] += cost
        if t in bd:
            bd[t] += inp + out

        if want_hours and ts is not None:
            hk = ts.astimezone().strftime("%Y-%m-%dT%H")  # local hour bucket
            bh = by_hour.setdefault(hk, {"hour": hk, "input_tokens": 0, "output_tokens": 0,
                                         "cost_usd": 0.0, "claude_api": 0, "codex": 0,
                                         "antigravity": 0})
            bh["input_tokens"] += inp
            bh["output_tokens"] += out
            bh["cost_usd"] += cost
            if t in bh:
                bh[t] += inp + out

    def _round(d):
        d["cost_usd"] = round(d["cost_usd"], 4)
        return d

    return {
        "totals": {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "total_tokens": total_in + total_out,
            "cache_read_tokens": total_cread,
            "cache_creation_tokens": total_ccreate,
            "cost_usd": round(total_cost, 4),
            "entries": kept,
        },
        "by_tool": [_round(v) for v in by_tool.values()],
        "by_model": sorted((_round(v) for v in by_model.values()),
                           key=lambda x: -x["input_tokens"] - x["output_tokens"]),
        "by_underlying_model": [],
        "by_project": sorted((_round({k: v for k, v in p.items() if k != "tools"} | {"tools": p["tools"]})
                              for p in by_project.values()),
                             key=lambda x: -x["input_tokens"] - x["output_tokens"]),
        "by_day": sorted((_round(v) for v in by_day.values()), key=lambda x: x["day"]),
        "by_hour": sorted((_round(v) for v in by_hour.values()), key=lambda x: x["hour"]),
    }


def read_local_summary(days: int = 30, tool: Optional[str] = None) -> dict:
    events: List[dict] = []
    if tool in (None, "claude_api"):
        events += read_claude_events(days)
    if tool in (None, "codex"):
        events += read_codex_events(days)
    if tool in (None, "antigravity"):
        events += read_antigravity_events(days)
    return aggregate(events, days, tool)


# ----- Claude subscription utilization -----
OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_BETA = "oauth-2025-04-20"
LIMITS_CACHE_TTL_S = 24 * 3600
_OAUTH_BACKOFF_UNTIL = 0.0  # set ahead on HTTP 429 to stop hammering the endpoint


def _read_claude_oauth_token() -> Optional[str]:
    cred = claude_dir() / ".credentials.json"
    try:
        data = json.loads(cred.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    o = data.get("claudeAiOauth") or {}
    expires = o.get("expiresAt", 0) or 0
    if expires and expires < time.time() * 1000:
        return None
    tok = o.get("accessToken")
    return tok if isinstance(tok, str) and tok else None


def _extract_oauth_percent(bucket: dict) -> Optional[float]:
    if not isinstance(bucket, dict):
        return None
    if bucket.get("utilization") is not None:
        try:
            return max(0.0, min(100.0, round(float(bucket["utilization"]))))
        except (ValueError, TypeError):
            return None
    for k in ("percent_used", "used_percent", "usage", "value"):
        if k in bucket and bucket[k] is not None:
            try:
                v = float(bucket[k])
            except (ValueError, TypeError):
                continue
            return max(0.0, min(100.0, round(v * 100 if v <= 1.5 else v)))
    return None


def _fetch_claude_oauth_limits() -> List[dict]:
    global _OAUTH_BACKOFF_UNTIL
    # Allow disabling the live network call (offline / privacy): falls back to cache.
    if os.environ.get("TOKENSCOPE_CLAUDE_OAUTH", "1").lower() in ("0", "false", "no"):
        return []
    if time.time() < _OAUTH_BACKOFF_UNTIL:  # in 429 backoff -> serve cache instead
        return []
    tok = _read_claude_oauth_token()
    if not tok:
        return []
    try:
        import requests  # available in requirements.txt

        resp = requests.get(
            OAUTH_USAGE_URL,
            headers={
                "Authorization": f"Bearer {tok}",
                "anthropic-beta": OAUTH_BETA,
                "User-Agent": "tokenscope",
            },
            timeout=8,
        )
        if resp.status_code == 429:
            _OAUTH_BACKOFF_UNTIL = time.time() + 300  # back off 5 min on rate limit
            return []
        if resp.status_code != 200:
            return []
        body = resp.json()
    except Exception:  # network/json errors must never crash the endpoint
        return []
    # Buckets are parsed dynamically because Anthropic renames the model-specific
    # weekly window over time (seven_day_sonnet -> seven_day_opus -> Fable, ...).
    known = {"five_hour": "5h", "seven_day": "All"}
    out = []
    for key, bk in body.items():
        if not isinstance(bk, dict):
            continue
        pct = _extract_oauth_percent(bk)
        if pct is None:
            continue
        if key in known:
            label = known[key]
        elif key.startswith("seven_day_"):
            label = key[len("seven_day_"):].replace("_", " ").title() + " only"
        else:
            continue
        out.append({"label": label, "used_percent": pct,
                    "reset": _reset_to_iso(bk.get("resets_at") or bk.get("reset_at"))})
    return out


def _read_claude_limits_cache() -> List[dict]:
    f = claude_rpc_dir() / "limits-cache.json"
    try:
        v = json.loads(f.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    if (time.time() * 1000 - (v.get("updatedAt", 0) or 0)) > LIMITS_CACHE_TTL_S * 1000:
        return []
    out = []
    for e in v.get("limits", []):
        if not isinstance(e, dict):
            continue
        try:
            p = e.get("used_percent")
            pct = None if p is None else max(0.0, min(100.0, float(p)))
        except (ValueError, TypeError):
            pct = None
        if pct is None:
            continue
        out.append({"label": e.get("label"), "used_percent": pct, "reset": _reset_to_iso(e.get("reset"))})
    return out


def _read_claude_subscription_type() -> Optional[str]:
    """e.g. 'max' / 'pro' / 'team' from the OAuth credentials, when signed in."""
    try:
        data = json.loads((claude_dir() / ".credentials.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    o = data.get("claudeAiOauth") or {}
    if not o.get("accessToken"):
        return None
    return o.get("subscriptionType")


def _detect_claude_account() -> Tuple[str, Optional[str]]:
    """Return (mode, plan): mode in {'subscription','api','none'}.
    subscription -> claude.ai OAuth (plan = subscriptionType, e.g. 'max').
    api -> API key / Claude Platform / Bedrock / Vertex / Foundry (plan = provider label).
    """
    if _read_claude_oauth_token():
        return ("subscription", _read_claude_subscription_type() or "subscription")
    # Token present but expired -> still a subscriber. Stay in 'subscription' mode so the
    # cache fallback keeps the panel populated instead of falsely showing "not signed in"
    # until Claude Code refreshes the token. (TokenScope reads the token, never refreshes it.)
    sub = _read_claude_subscription_type()
    if sub:
        return ("subscription", sub)

    base = (os.environ.get("ANTHROPIC_BASE_URL") or "").lower()
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    try:
        s = json.loads((claude_dir() / "settings.json").read_text(encoding="utf-8-sig"))
        if s.get("apiKeyHelper"):
            has_key = True
        env = s.get("env") or {}
        if env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"):
            has_key = True
        if not base and env.get("ANTHROPIC_BASE_URL"):
            base = str(env["ANTHROPIC_BASE_URL"]).lower()
    except (OSError, ValueError):
        pass
    try:
        cj = json.loads((_home() / ".claude.json").read_text(encoding="utf-8-sig"))
        if cj.get("primaryApiKey"):
            has_key = True
    except (OSError, ValueError):
        pass

    if "bedrock" in base:
        return ("api", "bedrock")
    if "aiplatform" in base or "vertex" in base:
        return ("api", "vertex")
    if "azure" in base or "foundry" in base:
        return ("api", "foundry")
    if has_key or base:
        return ("api", "Claude Platform")
    return ("none", None)


def _write_tokenscope_limits_cache(limits: List[dict]) -> None:
    """Persist the last good OAuth limits so transient failures keep showing values."""
    try:
        d = tokenscope_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "claude-limits-cache.json").write_text(
            json.dumps({"updatedAt": int(time.time() * 1000), "limits": limits})
        )
    except OSError:
        pass


def _read_tokenscope_limits_cache(ttl_s: int = 24 * 3600) -> List[dict]:
    f = tokenscope_dir() / "claude-limits-cache.json"
    try:
        v = json.loads(f.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    if (time.time() * 1000 - (v.get("updatedAt", 0) or 0)) > ttl_s * 1000:
        return []
    return [e for e in v.get("limits", []) if isinstance(e, dict)]


def read_claude_utilization() -> dict:
    mode, plan = _detect_claude_account()
    limits: List[dict] = []
    source = "none"
    if mode == "subscription":
        # Rolling-window quotas only exist on subscription accounts. Fallback chain keeps
        # the panel populated across transient OAuth failures:
        #   live OAuth -> claude-rpc cache -> our own persisted last-good cache.
        limits = _fetch_claude_oauth_limits()
        if limits:
            source = "oauth"
            _write_tokenscope_limits_cache(limits)
        else:
            limits = _read_claude_limits_cache()
            if limits:
                source = "cache"
            else:
                limits = _read_tokenscope_limits_cache()
                source = "cache" if limits else "none"
        order = {"5h": 0, "All": 1}
        limits = sorted(limits, key=lambda e: (order.get(e.get("label"), 9), str(e.get("label") or "")))
    return {
        "available": bool(limits),
        "mode": mode,            # subscription | api | none
        "source": source,
        "plan": plan,            # 'max'/'pro'/... or provider label for API
        "limits": limits,
    }


# ----- Codex subscription utilization -----
def _parse_codex_credits(c) -> Optional[float]:
    if isinstance(c, (int, float)):
        return c
    if isinstance(c, dict):
        if c.get("unlimited"):
            return None
        for k in ("remaining", "balance"):
            v = c.get(k)
            if isinstance(v, (int, float)):
                return v
            if isinstance(v, str):
                try:
                    return float(v)
                except ValueError:
                    pass
    return None


def _codex_limit(d) -> Optional[dict]:
    if not isinstance(d, dict) or d.get("used_percent") is None:
        return None
    return {
        "used_percent": round(float(d.get("used_percent") or 0.0), 1),
        "window_minutes": d.get("window_minutes"),
        "reset": _reset_to_iso(d.get("resets_at")),
    }


def _apply_codex_rollover(limit: Optional[dict], observed_iso: Optional[str]) -> Optional[dict]:
    if not limit or not limit.get("reset"):
        return limit
    rt = _parse_ts(limit["reset"])
    ot = _parse_ts(observed_iso)
    if rt and rt <= datetime.now(timezone.utc) and (ot is None or ot < rt):
        limit = dict(limit)
        limit["used_percent"] = 0.0
    return limit


def _read_codex_plan() -> Tuple[Optional[str], Optional[str]]:
    """Return (auth_mode, plan_type) without exposing any secret."""
    auth = codex_dir() / "auth.json"
    try:
        data = json.loads(auth.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return (None, None)
    auth_mode = data.get("auth_mode")
    plan = None
    tokens = data.get("tokens") or {}
    idt = tokens.get("id_token")
    if isinstance(idt, str) and idt:
        try:
            import jwt  # pyjwt, available in requirements.txt

            claims = jwt.decode(idt, options={"verify_signature": False})
            plan = (claims.get("https://api.openai.com/auth") or {}).get("chatgpt_plan_type")
        except Exception:
            plan = None
    return (auth_mode, plan)


def read_codex_utilization() -> dict:
    """Scan the newest rollouts (<=30d) for the latest non-null rate_limits.

    _apply_codex_rollover zeroes any window whose reset has passed, so a limit that hasn't
    been touched in a while still renders as 100% left instead of vanishing. The 24h window
    blanked the panel whenever Codex wasn't used in the last day, and never surfaced the
    GPT-5.3-Codex-Spark limits, which are logged only when Spark is actually used. 30 days
    is past both quota windows (5h / weekly), so any displayed number is either live or a
    correct 100%-left after rollover; the early-stop keeps the scan to a handful of files."""
    root = codex_dir() / "sessions"
    auth_mode, plan = _read_codex_plan()
    result = {
        "available": False,
        "auth_mode": auth_mode,
        "plan_type": plan,
        "primary": None, "secondary": None,
        "spark_primary": None, "spark_secondary": None,
        "spark_label": None, "credits": None,
        "observed_at": None,
    }
    if not root.exists():
        return result
    cutoff = time.time() - 30 * 86400
    files = []
    for fp in glob.iglob(str(root / "**/rollout-*.jsonl"), recursive=True):
        try:
            mt = os.path.getmtime(fp)
        except OSError:
            continue
        if mt >= cutoff:
            files.append((fp, mt))
    files.sort(key=lambda x: -x[1])

    codex_snap = spark_snap = None
    for fp, mt in files:
        try:
            with open(fp, "rb") as fh:
                size = os.path.getsize(fp)
                fh.seek(max(0, size - 256 * 1024))
                tail = fh.read().decode("utf-8", "replace")
        except OSError:
            continue
        for line in reversed(tail.split("\n")):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(o, dict) or o.get("type") != "event_msg":
                continue
            p = o.get("payload") or {}
            if p.get("type") != "token_count":
                continue
            rl = p.get("rate_limits")
            if not isinstance(rl, dict):
                continue
            lid = (rl.get("limit_id") or "")
            lname = (rl.get("limit_name") or "")
            is_spark = lid.startswith("codex_") or "spark" in lid.lower() or "spark" in lname.lower()
            ev_ts = _parse_ts(o.get("timestamp"))
            snap = {
                "primary": _codex_limit(rl.get("primary")),
                "secondary": _codex_limit(rl.get("secondary")),
                "credits": _parse_codex_credits(rl.get("credits")),
                "plan_type": rl.get("plan_type"),
                "limit_name": lname or None,
                "observed_at": ev_ts.isoformat() if ev_ts else _epoch_secs_to_iso(mt),
            }
            if is_spark:
                spark_snap = spark_snap or snap
            else:
                codex_snap = codex_snap or snap
            if codex_snap and spark_snap:
                break
        if codex_snap and spark_snap:
            break

    base = codex_snap or spark_snap
    if base:
        result["available"] = True
        result["primary"] = base["primary"]
        result["secondary"] = base["secondary"]
        result["credits"] = base["credits"]
        result["observed_at"] = base["observed_at"]
        if not result["plan_type"]:
            result["plan_type"] = base["plan_type"]
    if spark_snap:
        result["spark_primary"] = spark_snap["primary"]
        result["spark_secondary"] = spark_snap["secondary"]
        result["spark_label"] = spark_snap["limit_name"]

    # If a window's reset already passed (relative to when we observed it), it has rolled
    # over -> treat as freshly reset (0% used / 100% remaining).
    obs = result.get("observed_at")
    for k in ("primary", "secondary", "spark_primary", "spark_secondary"):
        result[k] = _apply_codex_rollover(result[k], obs)
    return result


# ===== Antigravity (Google) — local token usage =====
# Tokens: ~/.gemini/antigravity/conversations/*.db (SQLite "trajectory" DBs). Each
#   gen_metadata row is a protobuf blob for one model generation:
#     input = f1.4.2, output = f1.4.3, model name = f1.21 (fallback f1.19/f1.20),
#     timestamp = f1.9.4 (unix seconds). Project/workspace = trajectory_metadata_blob.
# Read-only; the encrypted *.pb conversation files are skipped. (No subscription /
#   live-quota panel: the cloudcode-pa quota fetch was unreliable and was removed;
#   antigravity_state_db() is still used by read_local_status for availability only.)
def gemini_dir() -> Path:
    return Path(os.environ.get("TOKENSCOPE_GEMINI_DIR") or (_home() / ".gemini"))


def antigravity_conv_dir() -> Path:
    return gemini_dir() / "antigravity" / "conversations"


def _appdata_dir() -> Path:
    """Per-user app-data root (where VSCode-fork apps like Antigravity keep their state)."""
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support"
    if os.name != "nt":
        return Path(os.environ.get("XDG_CONFIG_HOME") or (_home() / ".config"))
    return Path(os.environ.get("APPDATA") or (_home() / "AppData" / "Roaming"))


def antigravity_state_db() -> Path:
    return Path(os.environ.get("TOKENSCOPE_ANTIGRAVITY_STATE")
                or (_appdata_dir() / "Antigravity" / "User" / "globalStorage" / "state.vscdb"))


def antigravity_pricing(model_id: str) -> Tuple[str, float, float]:
    """Estimate (family, in_rate, out_rate) per 1M tokens for an Antigravity model.
    Subscription usage carries no per-token bill; these public list rates are a cost ESTIMATE."""
    b = (model_id or "").lower()
    if "claude" in b:
        return claude_pricing(model_id)
    if "gpt" in b or "oss" in b:
        return ("GPT-OSS", 0.15, 0.60)
    # Gemini public list rates per 1M tokens (Pro = the <=200K-token tier).
    if "flash" in b:
        if "lite" in b:
            return ("Gemini Flash Lite", 0.25, 1.50)   # Gemini 3.1 Flash Lite
        if "3.5" in b or "3-5" in b:
            return ("Gemini Flash", 1.50, 9.00)         # Gemini 3.5 Flash
        return ("Gemini Flash", 0.50, 3.00)             # Gemini 3 Flash (preview)
    if "pro" in b:
        return ("Gemini Pro", 2.0, 12.0)                # Gemini 3.x Pro (<=200K)
    return ("Gemini", 0.50, 3.00)


# --- tolerant protobuf wire reader (no .proto schema) ---
def _pb_rv(b, i):
    shift = 0; result = 0
    while True:
        x = b[i]; i += 1
        result |= (x & 0x7f) << shift
        if not x & 0x80:
            return result, i
        shift += 7


def _pb_fields(b) -> List[tuple]:
    out: List[tuple] = []; i = 0; n = len(b)
    try:
        while i < n:
            tag, i = _pb_rv(b, i)
            f = tag >> 3; wt = tag & 7
            if f == 0:
                break
            if wt == 0:
                v, i = _pb_rv(b, i); out.append((f, 0, v))
            elif wt == 2:
                ln, i = _pb_rv(b, i); out.append((f, 2, b[i:i + ln])); i += ln
            elif wt == 5:
                out.append((f, 5, b[i:i + 4])); i += 4
            elif wt == 1:
                out.append((f, 1, b[i:i + 8])); i += 8
            else:
                break
    except (IndexError, ValueError):
        pass
    return out


def _pb_msg(fields, num):
    for f, w, v in fields:
        if f == num and w == 2:
            return _pb_fields(v)
    return None


def _pb_str(fields, num):
    for f, w, v in fields:
        if f == num and w == 2:
            try:
                s = v.decode("utf-8")
                return s if s.isprintable() else None
            except UnicodeDecodeError:
                return None
    return None


def _pb_varint(fields, num):
    for f, w, v in fields:
        if f == num and w == 0:
            return v
    return None


def _ag_parse_gen(blob) -> Optional[Tuple[int, int, str, Optional[int]]]:
    """(input, output, model, ts_secs) from one gen_metadata protobuf blob, or None."""
    f1 = _pb_msg(_pb_fields(blob), 1)
    if not f1:
        return None
    inp = out = 0
    f4 = _pb_msg(f1, 4)
    if f4:
        inp = _pb_varint(f4, 2) or 0
        out = _pb_varint(f4, 3) or 0
    if inp == 0 and out == 0:
        return None
    model = _pb_str(f1, 21) or _pb_str(f1, 19)
    if not model:
        f20 = _pb_msg(f1, 20)
        if f20:
            model = _pb_str(f20, 2)
    ts = None
    f9 = _pb_msg(f1, 9)
    if f9:
        f9_4 = _pb_msg(f9, 4)
        if f9_4:
            for f, w, v in f9_4:
                if w == 0 and 1_600_000_000 < v < 2_000_000_000:
                    ts = v
                    break
    return (_safe_int(inp), _safe_int(out), model or "Gemini", ts)


_AG_FILE_RE = re.compile(rb"file://[^\x00-\x1f\"']{3,400}")


def _ag_workspace(blob: bytes) -> Optional[str]:
    m = _AG_FILE_RE.search(blob or b"")
    if not m:
        return None
    try:
        from urllib.parse import unquote
        uri = unquote(m.group(0).decode("utf-8", "replace"))
    except Exception:
        return None
    return re.sub(r"^file:/+", "", uri)  # file:///d:/path -> d:/path


def _ag_snapshot_db(path: str):
    """Copy a (possibly live) Antigravity SQLite DB plus its -wal/-shm sidecars to a temp
    dir and return (tmpdir, copy_path). immutable=1 on a changing file is undefined
    behavior and never sees WAL content; reading a private copy is safe and complete."""
    import shutil
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="tokenscope-ag-")
    dst = os.path.join(tmpdir, os.path.basename(path))
    shutil.copy2(path, dst)
    for suffix in ("-wal", "-shm"):
        side = path + suffix
        if os.path.exists(side):
            try:
                shutil.copy2(side, dst + suffix)
            except OSError:
                pass
    return tmpdir, dst


def _parse_antigravity_db(path: str, _unused=None) -> List[dict]:
    import shutil
    import sqlite3
    try:
        mtime_fallback = os.path.getmtime(path)
    except OSError:
        mtime_fallback = None
    try:
        tmpdir, snap = _ag_snapshot_db(path)
    except OSError:
        return []
    try:
        # Plain connect (not ro): SQLite may need to recover the copied WAL, which
        # requires write access. The copy is private, so this is harmless.
        con = sqlite3.connect(snap)
    except sqlite3.Error:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return []
    events: List[dict] = []
    try:
        cur = con.cursor()
        cwd = None
        try:
            row = cur.execute("SELECT data FROM trajectory_metadata_blob LIMIT 1").fetchone()
            if row and row[0]:
                cwd = _ag_workspace(row[0])
        except sqlite3.Error:
            pass
        try:
            rows = cur.execute("SELECT data FROM gen_metadata").fetchall()
        except sqlite3.Error:
            rows = []
        for (blob,) in rows:
            if not blob:
                continue
            g = _ag_parse_gen(blob)
            if not g:
                continue
            inp, out, model, ts_secs = g
            ts = None
            for cand in (ts_secs, mtime_fallback):
                if cand:
                    try:
                        ts = datetime.fromtimestamp(cand, tz=timezone.utc)
                        break
                    except (ValueError, OSError, OverflowError):
                        ts = None
            _lbl, in_rate, out_rate = antigravity_pricing(model)
            cost = inp / 1e6 * in_rate + out / 1e6 * out_rate
            events.append(_make_event("antigravity", model, cwd, ts, inp, out, 0, 0, cost))
    except sqlite3.Error:
        pass
    finally:
        con.close()
        shutil.rmtree(tmpdir, ignore_errors=True)
    return events


def read_antigravity_events(days: int) -> List[dict]:
    cutoff_ts = time.time() - days * 86400 - _MTIME_MARGIN_S
    return _collect_events(antigravity_conv_dir(), "*.db", _parse_antigravity_db, cutoff_ts)


# Throttle the utilization compute (the Claude OAuth call is rate-limited): the dashboard
# can poll often for tokens while OAuth is hit at most once per UTIL_TTL_S.
UTIL_TTL_S = 60
_UTIL_CACHE = {"ts": 0.0, "data": None}


def read_local_utilization(force: bool = False) -> dict:
    now = time.time()
    c = _UTIL_CACHE
    if not force and c["data"] is not None and (now - c["ts"]) < UTIL_TTL_S:
        return c["data"]
    data = {"claude": read_claude_utilization(), "codex": read_codex_utilization()}
    c["ts"] = now
    c["data"] = data
    return data


# ----- status (cheap availability probe) -----
def read_local_status() -> dict:
    # Note: deliberately does NOT return absolute filesystem paths (info disclosure);
    # only non-sensitive availability flags and a generic dir label.
    cdir = claude_dir()
    xdir = codex_dir()
    return {
        "claude": {
            "available": (cdir / "projects").exists(),
            "dir": "~/.claude",
            "has_oauth": bool(_read_claude_oauth_token()),
            "has_limits_cache": (claude_rpc_dir() / "limits-cache.json").exists(),
        },
        "codex": {
            "available": (xdir / "sessions").exists(),
            "dir": "~/.codex",
            "has_auth": (xdir / "auth.json").exists(),
        },
        "antigravity": {
            "available": antigravity_conv_dir().exists(),
            "dir": "~/.gemini/antigravity",
            "has_state": antigravity_state_db().exists(),
        },
    }
