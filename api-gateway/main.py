# api-gateway/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
import httpx
import os
import time

app = FastAPI(title="AI Platform API Gateway")
Instrumentator().instrument(app).expose(app)

VLLM_URL = os.environ.get("VLLM_URL", "").rstrip("/")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
MOCK_VLLM = os.environ.get("MOCK_VLLM", "0") == "1"
LANGCHAIN_API_KEY = os.environ.get("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.environ.get("LANGCHAIN_PROJECT", "lab28-platform")

_traceable = None
if LANGCHAIN_API_KEY:
    try:
        from langsmith import traceable

        _traceable = traceable
        os.environ.setdefault("LANGCHAIN_API_KEY", LANGCHAIN_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", LANGCHAIN_PROJECT)
    except ImportError:
        pass


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    embedding: list[float] = Field(default_factory=lambda: [0.0] * 384)


def _identity(fn):
    return fn


def _maybe_trace(name: str):
    if _traceable is not None:
        return _traceable(name=name)
    return _identity


@_maybe_trace("chat_inference")
async def _run_chat(query: str, embedding: list[float]) -> dict:
    start = time.time()
    context = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            search_resp = await client.post(
                f"{QDRANT_URL}/collections/documents/points/search",
                json={"vector": embedding, "limit": 3},
            )
            if search_resp.status_code == 200:
                context = search_resp.json().get("result", [])
    except httpx.HTTPError:
        context = []

    if MOCK_VLLM or not VLLM_URL or "your-vllm-tunnel" in VLLM_URL:
        latency = (time.time() - start) * 1000
        return {
            "answer": (
                f"Platform engineering is the discipline of designing and maintaining "
                f"self-service internal platforms for software delivery. "
                f"(mock response for query: {query})"
            ),
            "latency_ms": round(latency, 2),
            "model": "mock-vllm",
        }

    if not VLLM_URL:
        raise HTTPException(
            status_code=503,
            detail="VLLM_URL not configured. Set VLLM_NGROK_URL in .env and restart api-gateway.",
        )

    prompt = f"Context: {context}\n\nQuery: {query}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            llm_resp = await client.post(
                f"{VLLM_URL}/v1/chat/completions",
                json={
                    "model": VLLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            llm_resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="LLM inference timed out") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service unavailable: {exc}") from exc

    latency = (time.time() - start) * 1000
    result = llm_resp.json()
    return {
        "answer": result["choices"][0]["message"]["content"],
        "latency_ms": round(latency, 2),
        "model": result.get("model", VLLM_MODEL),
    }


@app.post("/api/v1/chat")
async def chat(body: ChatRequest):
    return await _run_chat(body.query, body.embedding)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin")
def admin():
    raise HTTPException(status_code=403, detail="Forbidden")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
