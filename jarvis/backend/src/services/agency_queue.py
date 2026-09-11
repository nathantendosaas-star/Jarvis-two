"""Agency Queue Service — Background task store for autonomous execution."""

import uuid
from typing import Dict, Any, List

_QUEUE: List[Dict[str, Any]] = []


def enqueue_task(title: str, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Enqueue a new task for background execution."""
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    item = {
        "id": task_id,
        "title": title,
        "type": task_type,
        "payload": payload,
        "status": "pending"
    }
    _QUEUE.append(item)
    return item


def list_queued_tasks() -> List[Dict[str, Any]]:
    """Retrieve list of queued autonomous agency tasks."""
    return list(_QUEUE)
