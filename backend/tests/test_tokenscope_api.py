"""TokenScope backend API tests."""
import os
import io
import json
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # Fall back to frontend .env (since backend tests need the public URL)
    from pathlib import Path
    env_file = Path("/app/frontend/.env")
    for line in env_file.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
            break

BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Root ----------
class TestRoot:
    def test_root_ok(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("name") == "TokenScope API"
        assert data.get("status") == "ok"


# ---------- Seed ----------
class TestSeed:
    def test_seed_inserts_demo_data(self, client):
        r = client.post(f"{API}/usage/seed")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "inserted" in data
        assert data["inserted"] > 200, f"Expected >200 inserted, got {data['inserted']}"


# ---------- Summary ----------
class TestSummary:
    def test_summary_structure(self, client):
        r = client.get(f"{API}/usage/summary", params={"days": 30})
        assert r.status_code == 200
        data = r.json()
        for key in ("totals", "by_tool", "by_model", "by_underlying_model", "by_day"):
            assert key in data, f"missing {key}"
        for k in ("input_tokens", "output_tokens", "total_tokens", "cost_usd", "entries"):
            assert k in data["totals"]
        assert data["totals"]["entries"] > 0
        assert isinstance(data["by_tool"], list)
        assert isinstance(data["by_model"], list)
        assert isinstance(data["by_underlying_model"], list)
        assert isinstance(data["by_day"], list)

    def test_antigravity_cost_positive(self, client):
        r = client.get(f"{API}/usage/summary", params={"days": 30})
        assert r.status_code == 200
        data = r.json()
        antigravs = [t for t in data["by_tool"] if t["tool"] == "antigravity"]
        assert len(antigravs) == 1, "antigravity tool missing from by_tool"
        assert antigravs[0]["cost_usd"] > 0, (
            f"Antigravity cost should be >0, got {antigravs[0]['cost_usd']}"
        )


# ---------- List ----------
class TestListUsage:
    def test_list_usage(self, client):
        r = client.get(f"{API}/usage", params={"days": 30})
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) > 0
        sample = items[0]
        for k in ("id", "tool", "model", "input_tokens", "output_tokens", "cost_usd", "timestamp"):
            assert k in sample, f"missing key {k}"


# ---------- Live ----------
class TestLive:
    def test_live(self, client):
        r = client.get(f"{API}/usage/live")
        assert r.status_code == 200
        data = r.json()
        assert "live" in data
        assert data["live"] is not None
        assert "tool" in data["live"]


# ---------- Threshold ----------
class TestThreshold:
    def test_get_threshold(self, client):
        r = client.get(f"{API}/threshold")
        assert r.status_code == 200
        data = r.json()
        assert "daily_tokens" in data
        assert "daily_cost_usd" in data

    def test_put_threshold(self, client):
        payload = {"daily_tokens": 500000, "daily_cost_usd": 25.0}
        r = client.put(f"{API}/threshold", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["daily_tokens"] == 500000
        assert data["daily_cost_usd"] == 25.0
        # Verify GET returns updated
        g = client.get(f"{API}/threshold").json()
        assert g["daily_tokens"] == 500000
        assert g["daily_cost_usd"] == 25.0


# ---------- Create / Delete ----------
class TestCreateDelete:
    def test_create_invalid_tool(self, client):
        r = client.post(f"{API}/usage", json={"tool": "bad_tool", "model": "x"})
        assert r.status_code == 400

    def test_create_valid_and_delete(self, client):
        payload = {
            "tool": "claude_api",
            "model": "claude-sonnet-4-5",
            "input_tokens": 1000,
            "output_tokens": 500,
        }
        r = client.post(f"{API}/usage", json=payload)
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["tool"] == "claude_api"
        assert entry["cost_usd"] > 0
        entry_id = entry["id"]

        # Delete
        d = client.delete(f"{API}/usage/{entry_id}")
        assert d.status_code == 200

        # Delete again should 404
        d2 = client.delete(f"{API}/usage/{entry_id}")
        assert d2.status_code == 404

    def test_create_antigravity_uses_underlying(self, client):
        payload = {
            "tool": "antigravity",
            "model": "antigravity",
            "underlying_model": "gemini-3-pro",
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
        }
        r = client.post(f"{API}/usage", json=payload)
        assert r.status_code == 200
        entry = r.json()
        # gemini-3-pro: 1.25 + 10 = 11.25
        assert abs(entry["cost_usd"] - 11.25) < 0.01, entry["cost_usd"]
        client.delete(f"{API}/usage/{entry['id']}")


# ---------- Import ----------
class TestImport:
    def test_csv_import(self):
        csv_content = (
            "tool,model,input_tokens,output_tokens,timestamp\n"
            "claude_api,claude-sonnet-4-5,1500,800,2026-01-15T10:00:00Z\n"
            "codex,gpt-5.2,2000,1200,2026-01-15T11:00:00Z\n"
        )
        files = {"file": ("test.csv", csv_content, "text/csv")}
        r = requests.post(f"{API}/usage/import", files=files)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["inserted"] == 2
        assert data["skipped"] == 0

    def test_json_import_list(self):
        payload = [
            {"tool": "antigravity", "model": "antigravity", "underlying_model": "gemini-3-pro",
             "input_tokens": 5000, "output_tokens": 2500, "timestamp": "2026-01-15T12:00:00Z"},
            {"tool": "claude_api", "model": "claude-haiku-4-5",
             "input_tokens": 100, "output_tokens": 50},
        ]
        files = {"file": ("test.json", json.dumps(payload), "application/json")}
        r = requests.post(f"{API}/usage/import", files=files)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["inserted"] == 2

    def test_json_import_entries_obj(self):
        payload = {"entries": [
            {"tool": "codex", "model": "gpt-5.2", "input_tokens": 100, "output_tokens": 50},
        ]}
        files = {"file": ("test.json", json.dumps(payload), "application/json")}
        r = requests.post(f"{API}/usage/import", files=files)
        assert r.status_code == 200
        assert r.json()["inserted"] == 1

    def test_import_skips_invalid_tool(self):
        csv_content = (
            "tool,model,input_tokens,output_tokens\n"
            "random_bad_tool,xyz,100,50\n"
        )
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        r = requests.post(f"{API}/usage/import", files=files)
        assert r.status_code == 200
        data = r.json()
        assert data["skipped"] >= 1


# ---------- Clear all ----------
class TestClearAll:
    def test_clear_all(self, client):
        # Run last (alphabetically TestZClear would be last, but we just call directly)
        r = client.delete(f"{API}/usage")
        assert r.status_code == 200
        assert "deleted" in r.json()
        # Re-seed for any later test usage outside of pytest run
        client.post(f"{API}/usage/seed")
