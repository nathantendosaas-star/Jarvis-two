# Technical Specification: Local Model Integration (`jarvis-local`) & Agent Bridge

## 1. Overview & Objective
JARVIS requires an offline fallback mode utilizing a local lightweight model (`qwen2.5-coder:1.5b-instruct` tagged as `jarvis-local` running on Ollama at `http://localhost:11434`).

When internet access is unavailable or when extremely simple offline operations are requested:
1. `jarvis-local` handles simple tasks via the agentic tool-use framework defined in `jarvis_agent_pro.py`.
2. All file modifications made while offline are staged into a `.staged_offline_changes/` directory or git workspace branch for online cloud model review before committing to GitHub.
3. `jarvis_agent_pro.py` is upgraded into an HTTP REST/FastAPI bridge server (or integrated directly into FastAPI `backend/src/api/` & `backend/src/services/`) to handle requests directly from the UI or backend orchestrator.

---

## 2. Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                 JARVIS Frontend (React / Vite)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / WebSockets
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             JARVIS FastAPI Backend / Bridge                 │
│                 (backend/src/services/ai.py)                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │ Online?                       │
          YES  ▼                               ▼ NO / Local Selected
┌──────────────────────────────┐ ┌──────────────────────────────┐
│ Cloud Model Orchestration    │ │ Local Model Engine           │
│ (Gemini / OpenRouter)        │ │ (Ollama: qwen2.5-coder:1.5b) │
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               │                               │
               │ Direct Commit                 │ Staged Writes
               ▼                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│ Git Repository Main Branch   │ │ .staged_offline_changes/     │
│                              │ │ (Awaits Cloud Model Review) │
└──────────────────────────────┘ └──────────────────────────────┘
```

---

## 3. Detailed Developer Implementation Tasks

### Task 1: Extend `jarvis_agent_pro.py` to expose an HTTP Bridge Server
- Convert `jarvis_agent_pro.py` into a Dual-Mode Execution Script (CLI & FastAPI/HTTP Server):
  - Add `uvicorn` / `FastAPI` or `http.server` endpoint `POST /api/local-agent/execute`.
  - Request Payload format:
    ```json
    {
      "task": "Create a helper function in utils.py",
      "session_id": "opt-session-id",
      "require_review": true
    }
    ```
  - Response Payload format:
    ```json
    {
      "status": "completed",
      "final_answer": "Created helper function in .staged_offline_changes/utils.py",
      "staged_files": ["utils.py"],
      "execution_log": [...]
    }
    ```

### Task 2: Implement Staged File Modifications for Offline Tasks
- Modify `write_file` and `edit_file` in `jarvis_agent_pro.py`:
  - When offline or `require_review=True`, instead of writing directly to `WORKSPACE_DIR/filename`, write to `WORKSPACE_DIR/.staged_offline_changes/filename`.
  - Maintain a JSON manifest `.staged_offline_changes/manifest.json`:
    ```json
    {
      "staged_at": "2025-02-23T12:00:00Z",
      "task": "Add utility function",
      "files": [
        {
          "original_path": "src/utils/math.ts",
          "staged_path": ".staged_offline_changes/src/utils/math.ts"
        }
      ]
    }
    ```

### Task 3: Integration into Backend (`backend/src/services/ai.py`)
- Add offline detection ping (`http://localhost:11434/api/tags` or health check to Ollama).
- If Ollama is responsive and `jarvis-local` is available while internet is unreachable:
  - Route user prompt to local model agent loop.
  - Return formatted response to Chat UI with a visual badge: `[OFFLINE MODE - Staged for Cloud Review]`.

### Task 4: Cloud Review & Sync Pipeline (When Back Online)
- Add a endpoint `POST /api/local-agent/review-staged` in `backend/src/api/agents.py`:
  - Reads `.staged_offline_changes/manifest.json`.
  - Sends diff / staged content to Gemini / OpenRouter model to perform static safety and syntax review.
  - If approved: merges staged files to actual workspace path and commits/pushes to GitHub or opens PR via Google Jules API workflow.
  - If rejected: provides feedback report and allows user correction.

---

## 4. Testing & Verification Checklist for Developers
1. **Ollama Connection:** Verify `ollama serve` and `ollama run jarvis-local` respond at `http://localhost:11434`.
2. **HTTP API:** Test `POST /api/local-agent/execute` with curl / Postman while offline.
3. **Staging Verification:** Confirm target workspace files remain untouched until cloud review approval.
4. **Stuck Loop & Safety:** Verify `BLOCKED_COMMAND_PATTERNS` and `STUCK_REPEAT_LIMIT` in `jarvis_agent_pro.py` function properly.

---

## 5. Developer Prompt / Hand-off Message
```text
Hey Dev Team,

Please implement the local model integration according to the specification above in `LOCAL_MODEL_INTEGRATION_SPEC.md`.
Specifically:
1. Turn `jarvis_agent_pro.py` into an HTTP REST server capable of receiving execution requests from JARVIS.
2. Route file writes/edits during offline mode into `.staged_offline_changes/` with a manifest tracking changes.
3. Hook up backend offline detection in `backend/src/services/ai.py` to route simple offline requests to `http://localhost:11434` / local bridge.
4. Build the cloud review pipeline (`/api/local-agent/review-staged`) so when online connection returns, Gemini/OpenRouter reviews and applies the staged offline edits.

Once completed, submit your implementation details for Jules review.
```
