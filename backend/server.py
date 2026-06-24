"""
TokenScope - Backend API for tracking token consumption across
Claude API, Codex (OpenAI) and Antigravity (Gemini/Claude/GPT).
"""
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query
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


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="TokenScope API")
api_router = APIRouter(prefix="/api")


# ----- Pricing reference (USD per 1M tokens) -----
# Used as a fallback when imported files do not provide cost.
PRICING = {
    # Anthropic Claude
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
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
    model: str
    underlying_model: Optional[str] = None  # for Antigravity: claude/gpt/gemini under the hood
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    session_id: Optional[str] = None
    note: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UsageEntryCreate(BaseModel):
    tool: str
    model: str
    underlying_model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None
    session_id: Optional[str] = None
    note: Optional[str] = None
    timestamp: Optional[datetime] = None


class Threshold(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: "global")
    daily_tokens: int = 1_000_000  # default 1M tokens per day
    daily_cost_usd: float = 10.0  # default $10 per day


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
        model=model,
        underlying_model=underlying,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        session_id=g("session_id", "session"),
        note=g("note", "notes"),
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


@api_router.get("/pricing")
async def get_pricing():
    return PRICING


@api_router.post("/usage", response_model=UsageEntry)
async def create_usage(payload: UsageEntryCreate):
    if payload.tool not in VALID_TOOLS:
        raise HTTPException(400, detail=f"tool must be one of {VALID_TOOLS}")
    return await _insert_entry(payload)


@api_router.get("/usage", response_model=List[UsageEntry])
async def list_usage(
    tool: Optional[str] = None,
    model: Optional[str] = None,
    days: Optional[int] = Query(default=30, ge=1, le=365),
    limit: int = Query(default=500, ge=1, le=5000),
):
    q: dict = {}
    if tool:
        q["tool"] = tool
    if model:
        q["model"] = model
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


@api_router.delete("/usage/{entry_id}")
async def delete_usage(entry_id: str):
    res = await db.usage.delete_one({"id": entry_id})
    if res.deleted_count == 0:
        raise HTTPException(404, detail="Entry not found")
    return {"ok": True}


@api_router.delete("/usage")
async def clear_usage():
    res = await db.usage.delete_many({})
    return {"deleted": res.deleted_count}


@api_router.post("/usage/import")
async def import_file(file: UploadFile = File(...)):
    """Import CSV or JSON file. JSON may be a list of entries or {entries:[...]}"""
    content = await file.read()
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
    except Exception as e:
        raise HTTPException(400, detail=f"Could not parse file: {e}")

    inserted = 0
    skipped = 0
    for r in rows:
        if not isinstance(r, dict):
            skipped += 1
            continue
        parsed = _parse_entry_row(r)
        if parsed is None:
            skipped += 1
            continue
        await _insert_entry(parsed)
        inserted += 1

    return {"inserted": inserted, "skipped": skipped, "total": len(rows)}


@api_router.post("/usage/seed")
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
async def get_summary(days: int = Query(default=30, ge=1, le=365)):
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


@api_router.get("/threshold", response_model=Threshold)
async def get_threshold():
    doc = await db.thresholds.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        t = Threshold()
        await db.thresholds.insert_one(t.model_dump())
        return t
    return Threshold(**doc)


@api_router.put("/threshold", response_model=Threshold)
async def update_threshold(payload: Threshold):
    payload.id = "global"
    await db.thresholds.update_one(
        {"id": "global"},
        {"$set": payload.model_dump()},
        upsert=True,
    )
    return payload


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
