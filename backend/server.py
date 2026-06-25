"""
TokenScope - Backend API for tracking token consumption across
Claude API, Codex (OpenAI) and Antigravity (Gemini/Claude/GPT).
"""
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query, Header, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import csv
import json
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import List, Optional, Annotated
from datetime import datetime, timezone, timedelta
from bson import ObjectId

import local_sources


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# ----- Security knobs -----
API_KEY = os.environ.get("TOKENSCOPE_API_KEY", "").strip()
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))  # 5 MB
MAX_IMPORT_ROWS = int(os.environ.get("MAX_IMPORT_ROWS", 50_000))

app = FastAPI(title="TokenScope API")


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """If TOKENSCOPE_API_KEY is set in the env, all writes require a matching header.
    If unset, this is a no-op (preserves the local-first default UX)."""
    if not API_KEY:
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
api_router = APIRouter(prefix="/api")


# ----- Pricing reference (USD per 1M tokens) -----
# Used as a fallback when imported files do not provide cost.
PRICING = {
    # Anthropic Claude
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    # Opus 4.5–4.8 are $5/$25 (listed before "claude-opus-4" so loose-match hits them first);
    # only the deprecated Opus 4 / 4.1 are $15/$75.
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-opus-4-7": {"input": 5.0, "output": 25.0},
    "claude-opus-4-6": {"input": 5.0, "output": 25.0},
    "claude-opus-4-5": {"input": 5.0, "output": 25.0},
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-fable-5": {"input": 10.0, "output": 50.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-haiku-4.5": {"input": 1.0, "output": 5.0},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    # OpenAI / Codex
    "gpt-5.2": {"input": 1.25, "output": 10.0},
    "gpt-5-2": {"input": 1.25, "output": 10.0},
    "gpt-5.4": {"input": 1.5, "output": 12.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4.1": {"input": 2.0, "output": 8.0},
    "codex-1": {"input": 1.25, "output": 10.0},
    # Google / Gemini (Antigravity)
    "gemini-3-pro": {"input": 1.25, "output": 10.0},
    "gemini-3.1-pro": {"input": 1.25, "output": 10.0},
    "gemini-3-flash": {"input": 0.30, "output": 2.50},
    "gemini-3.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}

VALID_TOOLS = {"claude_api", "codex", "antigravity"}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    key = (model or "").lower().strip()
    p = PRICING.get(key)
    if not p:
        # try loose match
        for k, v in PRICING.items():
            if k in key or key in k:
                p = v
                break
    if not p:
        return 0.0
    return round((input_tokens / 1_000_000) * p["input"] + (output_tokens / 1_000_000) * p["output"], 6)


# ----- Models -----
def _to_str(v):
    if isinstance(v, ObjectId):
        return str(v)
    return v


PyObjectId = Annotated[str, BeforeValidator(_to_str)]


class UsageEntry(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool: str  # claude_api | codex | antigravity
    model: str = Field(max_length=200)
    underlying_model: Optional[str] = Field(default=None, max_length=200)
    project: Optional[str] = Field(default=None, max_length=400)
    input_tokens: int = Field(default=0, ge=0, le=10**12)
    output_tokens: int = Field(default=0, ge=0, le=10**12)
    cost_usd: float = Field(default=0.0, ge=0.0, le=10**9)
    session_id: Optional[str] = Field(default=None, max_length=200)
    note: Optional[str] = Field(default=None, max_length=2000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UsageEntryCreate(BaseModel):
    tool: str
    model: str = Field(max_length=200)
    underlying_model: Optional[str] = Field(default=None, max_length=200)
    project: Optional[str] = Field(default=None, max_length=400)
    input_tokens: int = Field(default=0, ge=0, le=10**12)
    output_tokens: int = Field(default=0, ge=0, le=10**12)
    cost_usd: Optional[float] = Field(default=None, ge=0.0, le=10**9)
    session_id: Optional[str] = Field(default=None, max_length=200)
    note: Optional[str] = Field(default=None, max_length=2000)
    timestamp: Optional[datetime] = None


class Threshold(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: "global")
    daily_tokens: int = Field(default=1_000_000, ge=1, le=10**12)
    daily_cost_usd: float = Field(default=10.0, ge=0.0, le=10**9)


def _serialize(doc: dict) -> dict:
    """Strip _id and convert datetimes to iso strings for JSON-safe storage."""
    doc.pop("_id", None)
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].isoformat()
    return doc


def _parse_entry_row(row: dict) -> Optional[UsageEntryCreate]:
    """Normalize a row from CSV/JSON into UsageEntryCreate."""
    # Map common variant keys
    def g(*keys, default=None):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        return default

    tool = (g("tool", "source", "platform") or "").lower().replace("-", "_")
    if tool in ("claude", "anthropic"):
        tool = "claude_api"
    if tool in ("openai", "gpt"):
        tool = "codex"
    if tool not in VALID_TOOLS:
        return None

    model = str(g("model", "model_name") or "unknown").lower()
    underlying = g("underlying_model", "backend_model", "engine")
    if underlying:
        underlying = str(underlying).lower()

    project = g("project", "repo", "workspace", "cwd", "folder")
    if project:
        project = str(project).replace("\\", "/").rstrip("/").lower()[:400]

    try:
        input_tokens = int(g("input_tokens", "prompt_tokens", "in_tokens", default=0) or 0)
        output_tokens = int(g("output_tokens", "completion_tokens", "out_tokens", default=0) or 0)
    except (ValueError, TypeError):
        return None

    cost_raw = g("cost_usd", "cost", "price")
    try:
        cost = float(cost_raw) if cost_raw is not None else None
    except (ValueError, TypeError):
        cost = None

    ts_raw = g("timestamp", "date", "time", "created_at")
    ts = None
    if ts_raw:
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            ts = None

    return UsageEntryCreate(
        tool=tool,
        model=model[:200],
        underlying_model=(underlying[:200] if underlying else None),
        project=(project or None),
        input_tokens=max(0, min(input_tokens, 10**12)),
        output_tokens=max(0, min(output_tokens, 10**12)),
        cost_usd=(max(0.0, min(cost, 10**9)) if cost is not None else None),
        session_id=(str(g("session_id", "session"))[:200] if g("session_id", "session") else None),
        note=(str(g("note", "notes"))[:2000] if g("note", "notes") else None),
        timestamp=ts,
    )


async def _insert_entry(create: UsageEntryCreate) -> UsageEntry:
    # For Antigravity, the actual cost depends on the underlying model.
    pricing_model = create.underlying_model or create.model
    cost = create.cost_usd if create.cost_usd is not None else compute_cost(
        pricing_model, create.input_tokens, create.output_tokens
    )
    entry = UsageEntry(
        tool=create.tool,
        model=create.model,
        underlying_model=create.underlying_model,
        project=create.project,
        input_tokens=create.input_tokens,
        output_tokens=create.output_tokens,
        cost_usd=cost,
        session_id=create.session_id,
        note=create.note,
        timestamp=create.timestamp or datetime.now(timezone.utc),
    )
    doc = entry.model_dump()
    doc["timestamp"] = entry.timestamp.isoformat()
    await db.usage.insert_one(doc)
    return entry


# ----- Routes -----
@api_router.get("/")
async def root():
    return {"name": "TokenScope API", "status": "ok"}


@api_router.get("/auth/check")
async def auth_check(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Frontend uses this to know whether auth is required and if its key is valid."""
    if not API_KEY:
        return {"required": False, "valid": True}
    return {"required": True, "valid": bool(x_api_key and x_api_key == API_KEY)}


@api_router.get("/pricing")
async def get_pricing():
    return PRICING


@api_router.post("/usage", response_model=UsageEntry, dependencies=[Depends(require_api_key)])
async def create_usage(payload: UsageEntryCreate):
    if payload.tool not in VALID_TOOLS:
        raise HTTPException(400, detail=f"tool must be one of {VALID_TOOLS}")
    return await _insert_entry(payload)


@api_router.get("/usage", response_model=List[UsageEntry])
async def list_usage(
    tool: Optional[str] = None,
    model: Optional[str] = None,
    days: Optional[int] = Query(default=30, ge=1, le=100000),
    limit: int = Query(default=500, ge=1, le=5000),
):
    q: dict = {}
    if tool:
        q["tool"] = str(tool)
    if model:
        q["model"] = str(model)
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        q["timestamp"] = {"$gte": since}
    cursor = db.usage.find(q, {"_id": 0}).sort("timestamp", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    out: List[UsageEntry] = []
    for it in items:
        if isinstance(it.get("timestamp"), str):
            try:
                it["timestamp"] = datetime.fromisoformat(it["timestamp"])
            except ValueError:
                it["timestamp"] = datetime.now(timezone.utc)
        out.append(UsageEntry(**it))
    return out


@api_router.delete("/usage/{entry_id}", dependencies=[Depends(require_api_key)])
async def delete_usage(entry_id: str):
    res = await db.usage.delete_one({"id": entry_id})
    if res.deleted_count == 0:
        raise HTTPException(404, detail="Entry not found")
    return {"ok": True}


@api_router.delete("/usage", dependencies=[Depends(require_api_key)])
async def clear_usage():
    res = await db.usage.delete_many({})
    return {"deleted": res.deleted_count}


@api_router.post("/usage/import", dependencies=[Depends(require_api_key)])
async def import_file(file: UploadFile = File(...)):
    """Import CSV or JSON file. JSON may be a list of entries or {entries:[...]}.

    Hardened with: max body size, max row count, bulk insert.
    """
    # Read in chunks to enforce a hard size cap before exhausting RAM.
    buf = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {MAX_UPLOAD_BYTES} bytes)",
            )
    content = bytes(buf)
    filename = (file.filename or "").lower()
    rows: List[dict] = []
    try:
        if filename.endswith(".json") or content.lstrip().startswith(b"[") or content.lstrip().startswith(b"{"):
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, dict) and "entries" in data:
                rows = data["entries"]
            elif isinstance(data, list):
                rows = data
            else:
                rows = [data]
        else:
            text = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
    except UnicodeDecodeError:
        raise HTTPException(400, detail="File must be UTF-8 encoded")
    except json.JSONDecodeError as e:
        raise HTTPException(400, detail=f"Invalid JSON: {e.msg}")
    except csv.Error as e:
        raise HTTPException(400, detail=f"Invalid CSV: {e}")
    except Exception as e:
        raise HTTPException(400, detail=f"Could not parse file: {e}")

    if not isinstance(rows, list):
        raise HTTPException(400, detail="Top-level payload must be a list or object with 'entries'")

    truncated = False
    if len(rows) > MAX_IMPORT_ROWS:
        rows = rows[:MAX_IMPORT_ROWS]
        truncated = True

    docs: List[dict] = []
    skipped = 0
    for r in rows:
        if not isinstance(r, dict):
            skipped += 1
            continue
        parsed = _parse_entry_row(r)
        if parsed is None:
            skipped += 1
            continue
        pricing_model = parsed.underlying_model or parsed.model
        cost = parsed.cost_usd if parsed.cost_usd is not None else compute_cost(
            pricing_model, parsed.input_tokens, parsed.output_tokens
        )
        entry = UsageEntry(
            tool=parsed.tool,
            model=parsed.model,
            underlying_model=parsed.underlying_model,
            project=parsed.project,
            input_tokens=parsed.input_tokens,
            output_tokens=parsed.output_tokens,
            cost_usd=cost,
            session_id=parsed.session_id,
            note=parsed.note,
            timestamp=parsed.timestamp or datetime.now(timezone.utc),
        )
        doc = entry.model_dump()
        doc["timestamp"] = entry.timestamp.isoformat()
        docs.append(doc)

    inserted = 0
    if docs:
        result = await db.usage.insert_many(docs, ordered=False)
        inserted = len(result.inserted_ids)

    return {
        "inserted": inserted,
        "skipped": skipped,
        "total": len(rows),
        "truncated": truncated,
    }


@api_router.post("/usage/seed", dependencies=[Depends(require_api_key)])
async def seed_demo_data():
    """Generate demo data so the dashboard is immediately usable."""
    await db.usage.delete_many({})
    import random
    now = datetime.now(timezone.utc)
    demo_models = [
        ("claude_api", "claude-sonnet-4-5", None),
        ("claude_api", "claude-haiku-4-5", None),
        ("claude_api", "claude-opus-4-5", None),
        ("codex", "gpt-5.2", None),
        ("codex", "gpt-5.4", None),
        ("antigravity", "antigravity", "gemini-3-pro"),
        ("antigravity", "antigravity", "claude-sonnet-4-5"),
        ("antigravity", "antigravity", "gpt-5.2"),
        ("antigravity", "antigravity", "gemini-3-flash"),
    ]
    count = 0
    for d in range(14):
        for tool, model, underlying in demo_models:
            for _ in range(random.randint(1, 4)):
                inp = random.randint(500, 25000)
                out = random.randint(200, 12000)
                ts = now - timedelta(days=d, hours=random.randint(0, 23), minutes=random.randint(0, 59))
                await _insert_entry(UsageEntryCreate(
                    tool=tool, model=model, underlying_model=underlying,
                    input_tokens=inp, output_tokens=out, timestamp=ts,
                    session_id=f"sess-{uuid.uuid4().hex[:8]}",
                ))
                count += 1
    return {"inserted": count}


@api_router.get("/usage/summary")
async def get_summary(days: int = Query(default=30, ge=1, le=100000)):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cursor = db.usage.find({"timestamp": {"$gte": since}}, {"_id": 0})
    items = await cursor.to_list(length=10000)

    total_in = 0
    total_out = 0
    total_cost = 0.0
    by_tool: dict = {}
    by_model: dict = {}
    by_day: dict = {}
    by_underlying: dict = {}
    by_project: dict = {}

    for it in items:
        inp = it.get("input_tokens", 0) or 0
        outp = it.get("output_tokens", 0) or 0
        cost = it.get("cost_usd", 0.0) or 0.0
        total_in += inp
        total_out += outp
        total_cost += cost

        t = it.get("tool", "unknown")
        m = it.get("model", "unknown")
        u = it.get("underlying_model")
        proj = it.get("project") or "unassigned"

        bp = by_project.setdefault(proj, {
            "project": proj,
            "project_name": proj.split("/")[-1] if proj != "unassigned" else "unassigned",
            "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "entries": 0, "tools": {},
        })
        bp["input_tokens"] += inp
        bp["output_tokens"] += outp
        bp["cost_usd"] += cost
        bp["entries"] += 1
        bp["tools"][t] = bp["tools"].get(t, 0) + inp + outp

        bt = by_tool.setdefault(t, {"tool": t, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "entries": 0})
        bt["input_tokens"] += inp
        bt["output_tokens"] += outp
        bt["cost_usd"] += cost
        bt["entries"] += 1

        bm_key = f"{t}::{m}::{u or ''}"
        bm = by_model.setdefault(bm_key, {
            "tool": t, "model": m, "underlying_model": u,
            "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "entries": 0,
        })
        bm["input_tokens"] += inp
        bm["output_tokens"] += outp
        bm["cost_usd"] += cost
        bm["entries"] += 1

        if u:
            bu = by_underlying.setdefault(u, {"underlying_model": u, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            bu["input_tokens"] += inp
            bu["output_tokens"] += outp
            bu["cost_usd"] += cost

        ts = it.get("timestamp", "")
        day = ts[:10] if isinstance(ts, str) else ""
        bd = by_day.setdefault(day, {"day": day, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "claude_api": 0, "codex": 0, "antigravity": 0})
        bd["input_tokens"] += inp
        bd["output_tokens"] += outp
        bd["cost_usd"] += cost
        if t in bd:
            bd[t] += (inp + outp)

    # round costs
    for d in by_tool.values():
        d["cost_usd"] = round(d["cost_usd"], 4)
    for d in by_model.values():
        d["cost_usd"] = round(d["cost_usd"], 4)
    for d in by_day.values():
        d["cost_usd"] = round(d["cost_usd"], 4)
    for d in by_underlying.values():
        d["cost_usd"] = round(d["cost_usd"], 4)
    for d in by_project.values():
        d["cost_usd"] = round(d["cost_usd"], 4)

    return {
        "totals": {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "total_tokens": total_in + total_out,
            "cost_usd": round(total_cost, 4),
            "entries": len(items),
        },
        "by_tool": list(by_tool.values()),
        "by_model": sorted(by_model.values(), key=lambda x: -x["input_tokens"] - x["output_tokens"]),
        "by_underlying_model": list(by_underlying.values()),
        "by_project": sorted(by_project.values(), key=lambda x: -x["input_tokens"] - x["output_tokens"]),
        "by_day": sorted(by_day.values(), key=lambda x: x["day"]),
    }


@api_router.get("/usage/live")
async def get_live():
    """Latest single entry for system tray."""
    cursor = db.usage.find({}, {"_id": 0}).sort("timestamp", -1).limit(1)
    items = await cursor.to_list(length=1)
    if not items:
        return {"live": None}
    return {"live": items[0]}


# ----- Local source endpoints: read ~/.claude and ~/.codex directly (no DB) -----
# Defined as sync `def` so FastAPI runs them in a threadpool (the cold scan can take
# a few seconds) instead of blocking the event loop.
@api_router.get("/local/status")
def local_status():
    return local_sources.read_local_status()


@api_router.get("/local/summary")
def local_summary(
    days: int = Query(default=30, ge=1, le=100000),
    tool: Optional[str] = None,
):
    t = tool if tool in VALID_TOOLS else None
    return local_sources.read_local_summary(days=days, tool=t)


@api_router.get("/local/utilization")
def local_utilization():
    return local_sources.read_local_utilization()


@api_router.get("/threshold", response_model=Threshold)
async def get_threshold():
    doc = await db.thresholds.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        t = Threshold()
        await db.thresholds.insert_one(t.model_dump())
        return t
    return Threshold(**doc)


@api_router.put("/threshold", response_model=Threshold, dependencies=[Depends(require_api_key)])
async def update_threshold(payload: Threshold):
    payload.id = "global"
    await db.thresholds.update_one(
        {"id": "global"},
        {"$set": payload.model_dump()},
        upsert=True,
    )
    return payload


app.include_router(api_router)

# ----- CORS hardening -----
_raw_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '*').split(',') if o.strip()]
_wildcard = "*" in _raw_origins
_cors_kwargs = {
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "X-API-Key", "Authorization"],
    "expose_headers": [],
    "max_age": 600,
}
if _wildcard:
    # Wildcard + credentials is invalid per spec, disable credentials.
    _cors_kwargs["allow_origins"] = ["*"]
    _cors_kwargs["allow_credentials"] = False
else:
    _cors_kwargs["allow_origins"] = _raw_origins
    _cors_kwargs["allow_credentials"] = True

app.add_middleware(CORSMiddleware, **_cors_kwargs)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
