"""Planner Classifier & Request Analyzer — Classifies agency user requests into optimal workflow routes and specialist roles."""

import re
from typing import Dict, Any

SPECIALIST_ROLES = {
    "seo": "seo-specialist",
    "ad": "ad-copywriter",
    "copy": "ad-copywriter",
    "lead": "lead-researcher",
    "research": "lead-researcher",
    "audit": "client-auditor",
    "dev": "jules-developer",
    "code": "jules-developer",
}


def classify_request(prompt: str) -> Dict[str, Any]:
    """Classify prompt complexity, recommended agent persona, and execution tier."""
    prompt_lower = prompt.lower()

    matched_role = "lead-researcher"
    for key, role in SPECIALIST_ROLES.items():
        if key in prompt_lower:
            matched_role = role
            break

    word_count = len(prompt.split())
    is_complex = word_count > 15 or any(w in prompt_lower for w in ["build", "audit", "campaign", "scrape", "strategy", "analyze"])

    return {
        "prompt": prompt,
        "is_complex": is_complex,
        "recommended_role": matched_role,
        "requires_subagent": is_complex,
        "suggested_model": "deepseek/deepseek-v4-flash" if "research" in matched_role or "lead" in matched_role else "gemini-3.1-flash-lite"
    }
