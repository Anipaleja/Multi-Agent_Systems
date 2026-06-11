# Run from repo root: uvicorn api.server:app --reload
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from token_efficiency_model.combined_tactics.pipeline import TokenEfficientPipeline
from .auth import generate_api_key, hash_key
from .store import UsageStore

app = FastAPI(title="Brevitas Token Efficiency API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_store = UsageStore()
_pipelines: dict = {}


def _get_pipeline(key_hash: str) -> TokenEfficientPipeline:
    if key_hash not in _pipelines:
        _pipelines[key_hash] = TokenEfficientPipeline(savings_target=60.0, quality_floor=0.99)
    return _pipelines[key_hash]


def _authenticated(x_api_key: Optional[str] = Header(None)) -> str:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    kh = hash_key(x_api_key)
    if not _store.key_exists(kh):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return kh


# ── Key management ─────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    name: str = "default"


@app.post("/v1/keys")
def create_key(body: CreateKeyRequest):
    key = generate_api_key()
    kh = hash_key(key)
    _store.create_key(kh, body.name)
    return {"api_key": key, "name": body.name}


@app.get("/v1/keys")
def list_keys(_: str = Depends(_authenticated)):
    return {"keys": _store.list_keys()}


# ── Compression ─────────────────────────────────────────────────────────────

class CompressRequest(BaseModel):
    messages: List[str]
    prior_context: List[str] = []
    task: str = ""
    complexity: float = 0.5
    urgency: float = 0.5
    compression_level: int = 2
    prune_budget: int = 5
    delta_mode: str = "off"
    wire_mode: str = "json"


@app.post("/v1/compress")
def compress(body: CompressRequest, kh: str = Depends(_authenticated)):
    pipeline = _get_pipeline(kh)

    result = pipeline.process_task(
        task_text=body.task or (body.messages[0][:120] if body.messages else ""),
        incoming_messages=body.messages,
        prior_context=body.prior_context,
        complexity=body.complexity,
        urgency=body.urgency,
        compression_level=body.compression_level,
        prune_budget=body.prune_budget,
        delta_mode=body.delta_mode,
        wire_mode=body.wire_mode,
    )

    _store.record_usage(
        key_hash=kh,
        baseline_tokens=result.baseline_tokens,
        optimized_tokens=result.optimized_tokens,
        savings_pct=result.savings_pct,
        quality_proxy=result.quality_proxy,
    )

    return {
        "compressed_messages": result.debug.get("compressed_messages", []),
        "pruned_context": result.debug.get("pruned_context", []),
        "baseline_tokens": result.baseline_tokens,
        "optimized_tokens": result.optimized_tokens,
        "savings_pct": round(result.savings_pct, 2),
        "quality_proxy": round(result.quality_proxy, 4),
        "routed_model_hint": result.routed_model,
        "state_id": result.debug.get("state_id", ""),
    }


# ── Stats ───────────────────────────────────────────────────────────────────

@app.get("/v1/stats")
def stats(kh: str = Depends(_authenticated)):
    return _store.get_stats(kh)


@app.get("/v1/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
