"""
task_router.py

Decides whether an incoming task is a good fit for the local 1.5B model
(qwen2.5-coder:1.5b-instruct) or should be routed to the cloud model
(Gemini / OpenRouter) per LOCAL_MODEL_INTEGRATION_SPEC.md section 2.

Deliberately a plain heuristic classifier, not another LLM call — routing a
task shouldn't cost a model invocation, and a 1.5B model is not a reliable
judge of its own limits anyway.

This is the single highest-leverage safety piece of the integration: it's
what stops the small model from being handed something it will reliably
mangle (multi-file refactors, auth/payments/schema changes, anything with a
large blast radius).
"""

import re
from dataclasses import dataclass

# Signals that a task is too complex / too high-stakes for the local model,
# regardless of how short the request is worded.
FORCE_CLOUD_PATTERNS = [
    r"\bauth(entication|orization)?\b",
    r"\bpayment(s)?\b", r"\bstripe\b", r"\bmobile\s*money\b", r"\bmtn\b",
    r"\bmigrat(e|ion)\b", r"\brefactor\b",
    r"\bschema\b", r"\bdatabase\b", r"\bdb\s+migration\b",
    r"\bsecurity\b", r"\bencrypt", r"\bpassword\b", r"\bsecret\b", r"\bapi[\s_-]?key\b",
    r"\bdeploy(ment)?\b", r"\bdocker\b", r"\bci/cd\b", r"\bpipeline\b",
    r"\bdelete\b.*\b(database|table|repo|branch)\b",
    r"\bmulti[\s-]?file\b", r"\bentire\s+(project|codebase|repo)\b",
    r"\barchitecture\b", r"\bredesign\b",
]

# Signals that strongly suggest a small, contained, local-friendly task.
LOCAL_FRIENDLY_PATTERNS = [
    r"\brename\b", r"\bfix\s+(the\s+)?import\b", r"\badd\s+a?\s*function\b",
    r"\bformat(ting)?\b", r"\btypo\b", r"\bcomment(s)?\b",
    r"\blist\b", r"\bread\b", r"\bsearch\b", r"\bgrep\b",
    r"\bboilerplate\b", r"\bscaffold\b", r"\bsingle\s+file\b",
]

MAX_LOCAL_WORD_COUNT = 40   # long/compound requests tend to be multi-step, route to cloud
MAX_LOCAL_STEP_HINTS = 3    # count of "and"/"then"/"," as a rough multi-step proxy


@dataclass
class RouteDecision:
    route: str          # "local" or "cloud"
    reason: str
    matched: str = ""


def classify_task(goal: str) -> str:
    """Returns 'local' or 'cloud'. Use classify_task_verbose() if you want the reason."""
    return classify_task_verbose(goal).route


def classify_task_verbose(goal: str) -> RouteDecision:
    text = (goal or "").strip()
    if not text:
        return RouteDecision("cloud", "empty task")

    lower = text.lower()

    for pat in FORCE_CLOUD_PATTERNS:
        m = re.search(pat, lower)
        if m:
            return RouteDecision("cloud", "matched a high-stakes/complex keyword", m.group(0))

    word_count = len(text.split())
    if word_count > MAX_LOCAL_WORD_COUNT:
        return RouteDecision("cloud", f"task description too long ({word_count} words) — likely multi-step")

    step_hints = len(re.findall(r"\band\b|\bthen\b|,", lower))
    if step_hints > MAX_LOCAL_STEP_HINTS:
        return RouteDecision("cloud", f"task looks multi-step ({step_hints} conjunction/clause hints)")

    for pat in LOCAL_FRIENDLY_PATTERNS:
        m = re.search(pat, lower)
        if m:
            return RouteDecision("local", "matched a simple/contained task pattern", m.group(0))

    # Default: short, no red flags, no explicit green flag either — still local,
    # since MAX_STEPS/STUCK_REPEAT_LIMIT in jarvis_agent_pro.py act as a backstop
    # and staged writes mean nothing lands in the real workspace unreviewed.
    return RouteDecision("local", "short task, no complexity signals, defaulting to local")
