"""Compound Learning Failure Rules Engine — Error ledger converting mistake clusters into permanent operating rules."""

from pathlib import Path
from typing import List, Dict, Any

RULES_FILE = Path(__file__).resolve().parent.parent.parent.parent / "Cached" / "failure_rules.json"


def record_failure(error_type: str, details: str) -> Dict[str, Any]:
    """Record a system or subagent error into the ledger."""
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    rules = []
    if RULES_FILE.exists():
        try:
            import json
            rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            rules = []

    rule_entry = {"type": error_type, "details": details, "action": "Enforced strict validation constraint"}
    rules.append(rule_entry)

    import json
    RULES_FILE.write_text(json.dumps(rules, indent=2), encoding="utf-8")
    return {"success": True, "total_rules": len(rules)}
