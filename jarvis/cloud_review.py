"""
cloud_review.py

Implements LOCAL_MODEL_INTEGRATION_SPEC.md Task 4: when back online, staged
changes produced by the local model get reviewed by a cloud model before
they're allowed to merge into the real workspace.

Defaults to OpenRouter (matches Nathan's existing CLI agent setup — see
OPENROUTER_API_KEY / OPENROUTER_MODEL env vars) since that's already wired
into his other projects. Swapping to Gemini directly is a ~10 line change in
_call_reviewer_model() if preferred — the diff-building and manifest logic
above it don't need to change either way.

If no API key is configured, review_staged_changes() degrades gracefully:
it returns approved=False with a clear "no reviewer configured" message
instead of crashing, so the bridge endpoint stays usable in dev without
secrets set.
"""

import difflib
import os
from typing import Optional

import httpx

from jarvis_agent_pro import WORKSPACE_DIR, load_manifest, safe_path

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

REVIEW_SYSTEM_PROMPT = """You are a strict code reviewer checking changes made by a small, unsupervised local model before they are allowed into a real codebase.

For the diff you are given, check for:
- Syntax errors / obviously broken code
- Security issues (secrets, injected commands, unsafe eval, path traversal)
- Whether the change plausibly accomplishes the stated task
- Anything destructive or out of scope for the stated task

Respond in EXACTLY this format, nothing else:
VERDICT: APPROVE or REJECT
FEEDBACK: one or two sentences explaining why
"""


def build_diff(original_rel_path: str, staged_rel_path: str) -> str:
    """Unified diff between the real workspace file (if it exists) and the staged copy."""
    staged_abs = os.path.join(WORKSPACE_DIR, staged_rel_path)
    try:
        real_abs = safe_path(original_rel_path)
    except ValueError:
        real_abs = None

    original_lines = []
    if real_abs and os.path.exists(real_abs):
        with open(real_abs, "r", encoding="utf-8", errors="replace") as f:
            original_lines = f.readlines()

    staged_lines = []
    if os.path.exists(staged_abs):
        with open(staged_abs, "r", encoding="utf-8", errors="replace") as f:
            staged_lines = f.readlines()

    diff = difflib.unified_diff(
        original_lines, staged_lines,
        fromfile=f"a/{original_rel_path}", tofile=f"b/{original_rel_path}",
    )
    return "".join(diff) or "(no textual diff — file may be new or binary)"


async def _call_reviewer_model(diff_text: str, task: Optional[str], client: httpx.AsyncClient) -> dict:
    if not OPENROUTER_API_KEY:
        return {"approved": False, "feedback": "No cloud reviewer configured (OPENROUTER_API_KEY not set)."}

    user_content = f"Task: {task or '(not recorded)'}\n\nDiff:\n{diff_text[:6000]}"
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.0,
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}

    try:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return {"approved": False, "feedback": f"Cloud reviewer call failed: {e}"}

    approved = "VERDICT: APPROVE" in text.upper()
    feedback_line = ""
    for line in text.splitlines():
        if line.upper().startswith("FEEDBACK:"):
            feedback_line = line.split(":", 1)[1].strip()
    return {"approved": approved, "feedback": feedback_line or text.strip()}


async def review_staged_changes(client: httpx.AsyncClient) -> dict:
    """Reviews every file currently in the manifest. Returns a per-file verdict list.
    Does NOT apply or discard anything — the bridge endpoint decides that based on
    these verdicts (or a human decides via the UI)."""
    manifest = load_manifest()
    files = manifest.get("files", [])
    if not files:
        return {"reviewed": [], "message": "No staged changes to review."}

    results = []
    for entry in files:
        diff_text = build_diff(entry["original_path"], entry["staged_path"])
        verdict = await _call_reviewer_model(diff_text, manifest.get("task"), client)
        results.append({
            "original_path": entry["original_path"],
            "staged_path": entry["staged_path"],
            "approved": verdict["approved"],
            "feedback": verdict["feedback"],
        })
    return {"reviewed": results}
