"""Unit tests for local_sources (Claude/Codex local file readers).

Deterministic: builds synthetic ~/.claude and ~/.codex trees in a temp dir and
points local_sources at them via the TOKENSCOPE_*_DIR env overrides. Runs under
pytest, or standalone (`python tests/test_local_sources.py`) when pytest is absent.
"""
import json
import os
import sys
import time
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_sources as ls  # noqa: E402


def _build_tree(root: Path):
    now = datetime.now(timezone.utc)
    ts = lambda mins=0: (now - timedelta(minutes=mins)).isoformat().replace("+00:00", "Z")

    # ---- Claude ----
    cproj = root / ".claude" / "projects" / "D--Users-me-demo"
    cproj.mkdir(parents=True)
    cwd = "D:\\Users\\me\\demo"
    lines = [
        {"type": "user", "cwd": cwd, "timestamp": ts(10)},
        {"type": "assistant", "cwd": cwd, "timestamp": ts(9),
         "message": {"model": "claude-opus-4-8", "usage": {
             "input_tokens": 1000, "output_tokens": 500,
             "cache_read_input_tokens": 2000, "cache_creation_input_tokens": 400,
             "cache_creation": {"ephemeral_5m_input_tokens": 400, "ephemeral_1h_input_tokens": 0}}}},
        {"type": "assistant", "cwd": cwd, "timestamp": ts(8),
         "message": {"model": "claude-sonnet-4-5", "usage": {
             "input_tokens": 200, "output_tokens": 100,
             "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
        # synthetic / zero-usage line must be skipped
        {"type": "assistant", "cwd": cwd, "timestamp": ts(7),
         "message": {"model": "<synthetic>", "usage": {
             "input_tokens": 0, "output_tokens": 0,
             "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
    ]
    (cproj / "session1.jsonl").write_text(
        "\n".join(json.dumps(l) for l in lines), encoding="utf-8")

    # ---- Claude OAuth credentials (subscription = Max) ----
    (root / ".claude" / ".credentials.json").write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "fake-token", "refreshToken": "fake",
            "expiresAt": int(time.time() * 1000) + 3600 * 1000,
            "subscriptionType": "max", "scopes": ["user:inference"],
        }
    }), encoding="utf-8")

    # ---- Claude limits cache (fresh) ----
    crpc = root / ".claude-rpc"
    crpc.mkdir(parents=True)
    (crpc / "limits-cache.json").write_text(json.dumps({
        "updatedAt": int(time.time() * 1000),
        "limits": [
            {"label": "5h", "used_percent": 42, "reset": ts(-60)},
            {"label": "All", "used_percent": 10, "reset": ts(-1440)},
        ],
    }), encoding="utf-8")

    # ---- Codex ----
    xsess = root / ".codex" / "sessions" / "2026" / "06" / "25"
    xsess.mkdir(parents=True)
    xcwd = "d:\\Users\\me\\demo"
    resets = int(time.time()) + 3600
    xlines = [
        {"type": "session_meta", "timestamp": ts(6), "payload": {"cwd": xcwd}},
        {"type": "turn_context", "timestamp": ts(6), "payload": {"model": "gpt-5.5", "effort": "medium"}},
        # output_tokens already includes reasoning_output_tokens; total = input + output.
        {"type": "event_msg", "timestamp": ts(5), "payload": {"type": "token_count",
            "info": {"last_token_usage": {
                "input_tokens": 5000, "cached_input_tokens": 4000,
                "output_tokens": 300, "reasoning_output_tokens": 50, "total_tokens": 5300}},
            "rate_limits": {"limit_id": "codex", "plan_type": "prolite",
                "primary": {"used_percent": 18.0, "window_minutes": 300, "resets_at": resets},
                "secondary": {"used_percent": 7.0, "window_minutes": 10080, "resets_at": resets},
                "credits": None}}},
    ]
    (xsess / "rollout-2026-06-25T10-00-00-abc.jsonl").write_text(
        "\n".join(json.dumps(l) for l in xlines), encoding="utf-8")
    (root / ".codex" / "auth.json").write_text(json.dumps({
        "auth_mode": "chatgpt", "OPENAI_API_KEY": None, "tokens": {}}), encoding="utf-8")

    # config.toml top-level model (fallback)
    (root / ".codex" / "config.toml").write_text('model = "gpt-5.5"\n', encoding="utf-8")


def _setup(tmp):
    root = Path(tmp)
    _build_tree(root)
    os.environ["TOKENSCOPE_CLAUDE_DIR"] = str(root / ".claude")
    os.environ["TOKENSCOPE_CODEX_DIR"] = str(root / ".codex")
    os.environ["TOKENSCOPE_CLAUDE_RPC_DIR"] = str(root / ".claude-rpc")
    os.environ["TOKENSCOPE_DIR"] = str(root / ".tokenscope")
    os.environ["TOKENSCOPE_CLAUDE_OAUTH"] = "0"  # offline: no live OAuth call in tests
    # Isolate Antigravity too, so tests never read the host's real ~/.gemini data.
    os.environ["TOKENSCOPE_GEMINI_DIR"] = str(root / ".gemini")
    os.environ["TOKENSCOPE_ANTIGRAVITY_STATE"] = str(root / ".gemini" / "no-state.vscdb")
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("ANTHROPIC_BASE_URL", None)
    ls._FILE_CACHE.clear()
    ls._UTIL_CACHE["data"] = None


def _teardown():
    for k in ("TOKENSCOPE_CLAUDE_DIR", "TOKENSCOPE_CODEX_DIR", "TOKENSCOPE_CLAUDE_RPC_DIR",
              "TOKENSCOPE_DIR", "TOKENSCOPE_CLAUDE_OAUTH", "TOKENSCOPE_GEMINI_DIR",
              "TOKENSCOPE_ANTIGRAVITY_STATE", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
        os.environ.pop(k, None)
    ls._FILE_CACHE.clear()
    ls._UTIL_CACHE["data"] = None


def test_summary_per_project_and_tokens():
    with tempfile.TemporaryDirectory() as tmp:
        _setup(tmp)
        try:
            s = ls.read_local_summary(days=30)
            # one project, both tools present
            assert len(s["by_project"]) == 1, s["by_project"]
            proj = s["by_project"][0]
            assert proj["project_name"] == "demo"
            assert set(proj["tools"].keys()) == {"claude_api", "codex"}
            # Claude fresh input = 1000+200 ; Codex fresh input = 5000-4000 = 1000
            assert s["totals"]["input_tokens"] == 1000 + 200 + 1000
            assert s["totals"]["output_tokens"] == 500 + 100 + 300
            # synthetic zero-usage line skipped -> 3 token events total
            assert s["totals"]["entries"] == 3
            # cache tracked separately (claude 2000 read + codex 4000 cached)
            assert s["totals"]["cache_read_tokens"] == 2000 + 4000
            tools = {t["tool"]: t for t in s["by_tool"]}
            assert tools["claude_api"]["entries"] == 2
            assert tools["codex"]["entries"] == 1
            assert s["totals"]["cost_usd"] > 0
            # Codex cost (gpt-5.5 = 5/30 per Mtok): uncached=1000, cached=4000, out=300
            # = (1000*5 + 4000*5*0.1)/1e6 + 300*30/1e6 = 0.007 + 0.009 = 0.016
            # reasoning (50) is NOT added on top of output (it's already in output_tokens).
            assert tools["codex"]["cost_usd"] == 0.016
        finally:
            _teardown()


def test_gpt_5_6_pricing_tiers():
    assert ls.codex_pricing("gpt-5.6-sol")[1:] == (5.0, 30.0)
    assert ls.codex_pricing("GPT 5.6 Terra")[1:] == (2.5, 15.0)
    assert ls.codex_pricing("gpt-5-6-luna")[1:] == (1.0, 6.0)


def test_claude_utilization_cache_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        _setup(tmp)
        try:
            u = ls.read_claude_utilization()
            # OAuth disabled (offline) -> cache fallback; subscription detected = Max
            assert u["mode"] == "subscription"
            assert u["plan"] == "max"
            assert u["available"] is True
            assert u["source"] == "cache"
            labels = {l["label"]: l["used_percent"] for l in u["limits"]}
            assert labels["5h"] == 42
            assert labels["All"] == 10
        finally:
            _teardown()


def test_claude_api_mode_detected():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".claude" / "projects").mkdir(parents=True)  # exists but no credentials
        os.environ["TOKENSCOPE_CLAUDE_DIR"] = str(root / ".claude")
        os.environ["TOKENSCOPE_CODEX_DIR"] = str(root / ".codex")
        os.environ["TOKENSCOPE_CLAUDE_RPC_DIR"] = str(root / ".claude-rpc")
        os.environ["TOKENSCOPE_DIR"] = str(root / ".tokenscope")
        os.environ["TOKENSCOPE_CLAUDE_OAUTH"] = "0"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake"
        ls._FILE_CACHE.clear()
        ls._UTIL_CACHE["data"] = None
        try:
            u = ls.read_claude_utilization()
            # API key present, no subscription OAuth -> mode 'api', no rolling-window limits
            assert u["mode"] == "api"
            assert u["available"] is False
            assert u["limits"] == []
        finally:
            _teardown()


def test_codex_utilization_rate_limits():
    with tempfile.TemporaryDirectory() as tmp:
        _setup(tmp)
        try:
            c = ls.read_codex_utilization()
            assert c["available"] is True
            assert c["auth_mode"] == "chatgpt"
            assert c["plan_type"] == "prolite"
            assert c["primary"]["used_percent"] == 18.0
            assert c["primary"]["window_minutes"] == 300
            assert c["secondary"]["used_percent"] == 7.0
            assert c["primary"]["reset"] is not None
        finally:
            _teardown()


def test_missing_dirs_degrade_gracefully():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TOKENSCOPE_CLAUDE_DIR"] = str(Path(tmp) / "nope-claude")
        os.environ["TOKENSCOPE_CODEX_DIR"] = str(Path(tmp) / "nope-codex")
        os.environ["TOKENSCOPE_CLAUDE_RPC_DIR"] = str(Path(tmp) / "nope-rpc")
        os.environ["TOKENSCOPE_DIR"] = str(Path(tmp) / "nope-ts")
        os.environ["TOKENSCOPE_GEMINI_DIR"] = str(Path(tmp) / "nope-gemini")
        os.environ["TOKENSCOPE_ANTIGRAVITY_STATE"] = str(Path(tmp) / "nope-state.vscdb")
        ls._FILE_CACHE.clear()
        ls._UTIL_CACHE["data"] = None
        try:
            s = ls.read_local_summary(days=30)
            assert s["totals"]["entries"] == 0
            assert s["by_project"] == []
            st = ls.read_local_status()
            assert st["claude"]["available"] is False
            assert st["codex"]["available"] is False
            assert st["antigravity"]["available"] is False
            u = ls.read_local_utilization()
            assert u["claude"]["available"] is False
            assert u["codex"]["available"] is False
            assert "antigravity" not in u  # no subscription/quota panel for antigravity
        finally:
            _teardown()


# ---- Antigravity: protobuf wire encoder for synthetic fixtures ----
def _pv(n):  # varint
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _pld(num, data):  # length-delimited field (msg/string/bytes)
    return _pv((num << 3) | 2) + _pv(len(data)) + data


def _pvf(num, val):  # varint field
    return _pv((num << 3) | 0) + _pv(val)


def _ag_gen_blob(inp, out, model, ts):
    f4 = _pvf(2, inp) + _pvf(3, out)                 # f1.4.{2=in,3=out}
    f9 = _pld(4, _pvf(1, ts))                        # f1.9.4.1 = ts secs
    f1 = _pld(4, f4) + _pld(21, model.encode()) + _pld(9, f9)
    return _pld(1, f1)


def _write_ag_db(path, workspace, gens):
    import sqlite3
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE trajectory_metadata_blob(id TEXT, data BLOB)")
    con.execute("CREATE TABLE gen_metadata(idx INTEGER, data BLOB, size INTEGER)")
    con.execute("INSERT INTO trajectory_metadata_blob VALUES(?,?)",
                ("main", _pld(1, ("file://" + workspace).encode())))
    for i, (inp, out, model, ts) in enumerate(gens):
        blob = _ag_gen_blob(inp, out, model, ts)
        con.execute("INSERT INTO gen_metadata VALUES(?,?,?)", (i, blob, len(blob)))
    con.commit()
    con.close()


def test_antigravity_gen_decode_and_pricing():
    ts = int(time.time()) - 600
    blob = _ag_gen_blob(29027, 191, "Gemini 3.5 Flash (Medium)", ts)
    inp, out, model, got_ts = ls._ag_parse_gen(blob)
    assert (inp, out, model, got_ts) == (29027, 191, "Gemini 3.5 Flash (Medium)", ts)
    # family-based pricing vs Google/Anthropic list rates (per 1M tokens)
    assert ls.antigravity_pricing("Gemini 3.5 Flash (Medium)")[1:] == (1.50, 9.00)
    assert ls.antigravity_pricing("Gemini 3.1 Flash Lite")[1:] == (0.25, 1.50)
    assert ls.antigravity_pricing("Gemini 3.1 Pro (High)")[1:] == (2.0, 12.0)
    assert ls.antigravity_pricing("Claude Sonnet 4.6 (Thinking)")[1:] == (3.0, 15.0)
    assert ls.antigravity_pricing("Claude Opus 4.6 (Thinking)")[1:] == (5.0, 25.0)
    assert ls.antigravity_pricing("GPT-OSS 120B")[1:] == (0.15, 0.60)


def test_antigravity_db_events():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        conv = root / ".gemini" / "antigravity" / "conversations"
        conv.mkdir(parents=True)
        ts = int(time.time()) - 600
        _write_ag_db(conv / "c1.db", "/d:/Users/me/agproj",
                     [(1000, 200, "Gemini 3 Flash", ts), (500, 50, "Claude Opus 4.6 (Thinking)", ts)])
        os.environ["TOKENSCOPE_GEMINI_DIR"] = str(root / ".gemini")
        os.environ["TOKENSCOPE_ANTIGRAVITY_STATE"] = str(root / "no-state.vscdb")
        ls._FILE_CACHE.clear()
        ls._UTIL_CACHE["data"] = None
        try:
            ev = ls.read_antigravity_events(30)
            assert len(ev) == 2, ev
            assert all(e["tool"] == "antigravity" for e in ev)
            assert {e["project_name"] for e in ev} == {"agproj"}
            s = ls.read_local_summary(days=30, tool="antigravity")
            assert s["totals"]["input_tokens"] == 1500
            assert s["totals"]["output_tokens"] == 250
            assert s["totals"]["entries"] == 2
            assert s["totals"]["cost_usd"] > 0
            st = ls.read_local_status()
            assert st["antigravity"]["available"] is True
        finally:
            _teardown()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
