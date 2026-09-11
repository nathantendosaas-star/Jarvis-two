# Master Architecture & Implementation Plan for JARVIS System Upgrades

Based on `errorstofix.txt` and `antigravity-clone-spec.md`, this master plan details the architecture and step-by-step implementation for all 10 system components.

---

## 1. Coding / Developer Agent Workflow (Google Jules API Integration)
* **Goal:** Developer agents do not use Gemini/OpenRouter directly for unchecked file writes. All coding tasks are executed via GitHub PR workflows using the Google Jules API.
* **Backend Changes (`backend/src/services/ai.py` & `backend/src/api/agents.py`):**
  - Implement a dedicated `JulesDeveloperAgent` service.
  - On developer task request: create a branch, post prompt/task to Google Jules API / GitHub integration, generate PR.
  - Perform automated PR review, merge upon approval, and execute `git pull` locally in workspace.

---

## 2. Research Agent Workflow (Gemini CEO Spec -> OpenRouter DeepSeek/Gemma Researcher)
* **Goal:** Split research into 2 stages: Spec Generation (Gemini API) -> Execution (OpenRouter API).
* **Backend Workflow:**
  - **Stage 1 (CEO Orchestrator):** Gemini API receives research prompt and outputs a structured Markdown spec (`Cached/research_specs/<task_id>.md`).
  - **Stage 2 (Researcher Subagent):** Researcher subagent runs strictly using OpenRouter (`deepseek/deepseek-v4-flash` or `google/gemma-2-27b-it`), reading `<task_id>.md` as system guidance to execute web fetching, synthesis, and final report generation.

---

## 3. Offline Tasks (`jarvis-local` & `jarvis_agent_pro.py`)
* **Goal:** Enable offline task execution using `qwen2.5-coder:1.5b-instruct` on Ollama (`http://localhost:11434`) via an HTTP bridge server.
* **Key Implementation:**
  - Detailed in `LOCAL_MODEL_INTEGRATION_SPEC.md`.
  - Upgrades `jarvis_agent_pro.py` to FastAPI/HTTP server.
  - Off-line edits saved to `.staged_offline_changes/` with `manifest.json`.
  - Cloud review endpoint (`POST /api/local-agent/review-staged`) reviews and merges staged edits when back online.

---

## 4. Subagent Spawning & Registration (`antigravity-clone-spec.md` Alignment)
* **Goal:** Fix subagent creation from Chat interface/voice commands and ensure spawned subagents register correctly in database and Agent Registry.
* **Backend Fixes (`backend/src/services/ai.py`, `backend/src/api/agents.py`):**
  - Fix tool handler for `invoke_subagent` / `spawn_subagent`.
  - Persist newly created agents into SQLite DB with initial status `active` so they immediately appear in the Agents view.
  - Support fallback to Gemini API subagent for general simple tasks.
  - Implement isolated context (`messages: []`) per subagent as specified in Antigravity 2.0.

---

## 5. Memory Page Enhancements (Graph, Cache Sharing, Search & Scrolling)
* **Frontend (`src/components/MemoryView.tsx`, `NeuralNetworkGraph.tsx`):**
  - **Graph Topology:** Connect every memory node to every other node (full mesh/fully connected topology) and link all nodes to a central `OS CORE` node.
  - **Scrolling:** Add `overflow-y-auto max-h-screen` container wrapper.
* **Backend Cache Sharing & Search (`backend/src/api/memories.py`):**
  - Grant all agents access to shared cache in `Cached/`.
  - Fix Memory Search endpoint to perform full-text search across SQLite DB and `Cached/*.md` files.
  - Integrate OpenRouter `deepseek/deepseek-v4-flash` to generate a 5-sentence concise summary of search query results.

---

## 6. Dashboard Fixes (Stationary Milestones, Scrolling, Chatbox & Notifications)
* **Frontend (`src/components/HUDView.tsx`, `DashboardView.tsx`):**
  - **Milestones:** Fix CSS layout/positioning to prevent milestone components from sliding downward out of view (remove unstable absolute translations/animations).
  - **Scrolling:** Wrap main view in `overflow-y-auto`.
  - **Fullscreen Chatbox:** Ensure `ChatView` overlay / bottom input panel has fixed `z-index` and position so it remains visible and interactable in fullscreen mode.
  - **Notifications Modal:** Add click-outside backdrop listener (`onClick={() => setShowNotifications(false)}`) to dismiss notifications modal when clicking anywhere on screen.

---

## 7. Agents Page Performance Optimization
* **Frontend (`src/components/AgentsView.tsx`):**
  - Remove heavy real-time SVG/Canvas performance line graphs from active/idle agent cards.
  - Replace graphs with lightweight live numeric metric badges (e.g., `Active Tasks: 3`, `Tokens: 12.4k`, `Latency: 45ms`).

---

## 8. Browser Integration & Fallback Navigation
* **Frontend (`src/components/BrowserView.tsx`) & Backend (`backend/src/services/ai.py`):**
  - Replace "No browser automation backend is connected" alert with an automated fallback pipeline:
    1. Attempt Playwright DOM automation if browser service active.
    2. Fallback seamlessly to `web_fetch` (requests/BeautifulSoup clean HTML text renderer) and present cleaned web content directly in browser viewport.

---

## 9. Automations Engine (Plain English Automation Creator)
* **Backend (`backend/src/api/tasks.py` / new automations service) & Frontend (`src/components/AutomationView.tsx`):**
  - Add Gemini API prompt handler to convert plain English user descriptions (e.g., "Check weather every morning at 8am and post to chat") into executable automation JSON schemas (trigger, schedule, actions).
  - Support creating automations directly via Chat UI command (`"Create automation: ..."`) and from Automations page form.

---

## 10. Global UI Scrollability Audit
* Ensure top-level container styles in `src/App.tsx` and all view components (`DashboardView`, `HUDView`, `AgentsView`, `MemoryView`, `AutomationView`, `BrowserView`, `ProjectsView`, `SettingsView`, `ChatView`) use `overflow-y-auto h-full` to allow smooth scrolling on all screen sizes.
