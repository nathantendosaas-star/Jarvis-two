"""In-memory async event broker for decoupled service communication."""

import asyncio
from typing import Dict, List, Callable, Any


class EventBroker:
    """Lightweight pub/sub using asyncio. No external broker needed."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers.setdefault(event_type, []).append(handler)

    async def publish(self, event_type: str, data: Any = None):
        for handler in self._subscribers.get(event_type, []):
            if asyncio.iscoroutinefunction(handler):
                asyncio.create_task(handler(data))
            else:
                handler(data)


# Singleton instance used across all services
event_broker = EventBroker()
