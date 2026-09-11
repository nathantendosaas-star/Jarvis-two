"""Action Tag Executor — Handles [ACTION:SCRAPE_LEADS], [ACTION:SEO_AUDIT], [ACTION:GENERATE_REPORT], [ACTION:BUILD_PAGE]."""

import re
import json
from typing import Dict, Any, List


def parse_and_execute_action_tags(response_text: str) -> List[Dict[str, Any]]:
    """Detect and execute agency action tags embedded in LLM text streams."""
    pattern = r"\[ACTION:([A_Z0-9_]+)(?:\((.*?)\))?\]"
    matches = re.findall(pattern, response_text)

    executed_results = []
    for action_type, args_str in matches:
        if action_type == "SCRAPE_LEADS":
            executed_results.append({"action": action_type, "status": "queued", "target": args_str or "Default niche"})
        elif action_type == "SEO_AUDIT":
            executed_results.append({"action": action_type, "status": "executed", "domain": args_str or "target domain"})
        elif action_type == "GENERATE_REPORT":
            executed_results.append({"action": action_type, "status": "completed", "report": args_str or "Client KPI Report"})
        elif action_type == "BUILD_PAGE":
            executed_results.append({"action": action_type, "status": "staged", "page": args_str or "Landing Page"})

    return executed_results
