"""Importance Gate Filter — Mem0 pattern importance scoring threshold gate (score >= 3)."""

from typing import Dict, Any


def evaluate_importance(text: str, user_importance: int = 5) -> int:
    """Calculate importance score (1-10) for saving facts into agency memory bank."""
    score = min(10, max(1, user_importance))
    keywords = ["client", "credential", "rule", "strategy", "revenue", "campaign", "lead", "api"]
    if any(k in text.lower() for k in keywords):
        score = max(score, 6)
    return score


def should_store_memory(score: int) -> bool:
    """Threshold filter gate (score >= 3)."""
    return score >= 3
