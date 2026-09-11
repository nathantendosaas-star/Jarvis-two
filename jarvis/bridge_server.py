"""
bridge_server.py

HTTP + WebSocket bridge exposing jarvis_agent_pro's local-model agent loop to
the browser JARVIS UI, per LOCAL_MODEL_INTEGRATION_SPEC.md Task 1.

Run:
    uvicorn bridge_server:app --host 0.0.0.0 --port 8008

Endpoints:
    GET  /api/local-agent/health            -> Ollama reachability + model check
    POST /api/local-agent/execute           -> run a task, get one JSON response back
    WS   /ws/local-agent/execute            -> run a task, get live step-by-step events
    GET  /api/local-agent/staged            -> list currently staged (unreviewed) changes
    POST /api/local-agent/review-staged     -> send staged diffs to the cloud reviewer
    POST /api/local-agent/staged/apply      -> merge one staged file into the real workspace
    POST /api/local-agent/staged/discard    -> throw away one staged file

Design notes for efficiency:
    - A single shared httpx.AsyncClient is reused across all requests (connection
      pooling to Ollama) instead of opening a new connection per call.
    - The agent loop itself is async end-to-end (jarvis_agent_pro.stream_ollama_async
      streams tokens from Ollama as they're generated), so FastAPI can serve multiple
      browser sessions concurrently without one task blocking another, and the
      WebSocket path forwards model output to the browser as it's generated instead
      of waiting for the full multi-step task to finish.
    - REST /execute is a thin wrapper that drains the same async generator the
      WebSocket uses — no duplicated agent logic.
"""

import os
from typing import List, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from jarvis_agent_pro import (
    SYSTEM_PROMPT,
    MODEL_NAME,
    run_agentic_workflow_async,
    stream_agentic_workflow_async,
    load_manifest,
    apply_staged_file,
    discard_staged_file,
)
from task_router import classify_task_verbose
from cloud_review import review_staged_changes

app = FastAPI(title="JARVIS Local Agent Bridge")

# Comma-separated list of allowed browser origins for the JARVIS UI, e.g.
# "http://localhost:5173,https://jarvis.masembegroup.com"
_origins = os.environ.get("JARVIS_UI_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def _startup():
    global _client
    _client = httpx.AsyncClient()


@app.on_event("shutdown")
async def _shutdown():
    if _client:
        await _client.aclose()


# =============================================================================
# Schemas
# =============================================================================
class ExecuteRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    require_review: bool = True     # True -> staged writes; False -> direct writes (use with care)
    force_local: bool = False       # bypass the router (e.g. UI has an explicit "use local model" toggle)


class ExecuteResponse(BaseModel):
    status: str
    final_answer: str
    staged_files: List[str]
    execution_log: list
    routed_to: str
    route_reason: str


class StagedPathRequest(BaseModel):
    original_path: str


# =============================================================================
# Health / offline-detection (spec Task 3)
# =============================================================================
@app.get("/api/local-agent/health")
async def health():
    try:
        r = await _client.get("http://localhost:11434/api/tags", timeout=3.0)
        r.raise_for_status()
        tags = [m.get("name", "") for m in r.json().get("models", [])]
        available = any(t == MODEL_NAME or t.startswith(f"{MODEL_NAME}:") for t in tags)
        return {"ollama_up": True, "models": tags, "jarvis_local_available": available}
    except Exception as e:
        return {"ollama_up": False, "error": str(e), "jarvis_local_available": False}


# =============================================================================
# Execute (spec Task 1)
# =============================================================================
@app.post("/api/local-agent/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    if req.force_local:
        route, reason = "local", "force_local flag set by caller"
    else:
        decision = classify_task_verbose(req.task)
        route, reason = decision.route, decision.reason

    if route == "cloud":
        return ExecuteResponse(
            status="rejected_route_to_cloud",
            final_answer="This task was classified as too complex/high-stakes for the local model. Route it to the cloud model instead.",
            staged_files=[], execution_log=[], routed_to="cloud", route_reason=reason,
        )

    result = await run_agentic_workflow_async(
        req.task, SYSTEM_PROMPT + "\n", _client, staged=req.require_review
    )
    return ExecuteResponse(
        status=result["status"],
        final_answer=result["final_answer"],
        staged_files=result["staged_files"],
        execution_log=result["execution_log"],
        routed_to="local",
        route_reason=reason,
    )


@app.websocket("/ws/local-agent/execute")
async def execute_ws(ws: WebSocket):
    """Live step-by-step feed for the browser UI. Expected first client message:
    {"task": "...", "require_review": true, "force_local": false}

    Server events (see stream_agentic_workflow_async docstring for the full list):
      {"type": "routed", "routed_to": "local", "reason": "..."}
      {"type": "rejected", "reason": "...", "message": "..."}
      {"type": "step_start" | "token" | "thought_complete" | "tool_call" |
                "observation" | "parse_error" | "aborted" | "max_steps_reached" | "final", ...}
    """
    await ws.accept()
    try:
        payload = await ws.receive_json()
        task = payload.get("task", "")
        require_review = payload.get("require_review", True)
        force_local = payload.get("force_local", False)

        if force_local:
            route, reason = "local", "force_local flag set by caller"
        else:
            decision = classify_task_verbose(task)
            route, reason = decision.route, decision.reason

        if route == "cloud":
            await ws.send_json({"type": "rejected", "reason": reason,
                                 "message": "Task classified as too complex for the local model."})
            await ws.close()
            return

        await ws.send_json({"type": "routed", "routed_to": "local", "reason": reason})

        async for event in stream_agentic_workflow_async(task, SYSTEM_PROMPT + "\n", _client, staged=require_review):
            await ws.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# =============================================================================
# Staged changes (spec Task 2 + Task 4)
# =============================================================================
@app.get("/api/local-agent/staged")
async def list_staged():
    return load_manifest()


@app.post("/api/local-agent/review-staged")
async def review_staged():
    """Sends every currently staged diff to the cloud reviewer. Does not apply
    or discard anything by itself — returns verdicts for the UI/user to act on
    (or for the UI to auto-call /staged/apply on approved files, if desired)."""
    return await review_staged_changes(_client)


@app.post("/api/local-agent/staged/apply")
async def apply_staged(req: StagedPathRequest):
    message = apply_staged_file(req.original_path)
    ok = message.startswith("Applied")
    return {"ok": ok, "message": message}


@app.post("/api/local-agent/staged/discard")
async def discard_staged(req: StagedPathRequest):
    message = discard_staged_file(req.original_path)
    ok = message.startswith("Discarded")
    return {"ok": ok, "message": message}
