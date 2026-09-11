"""Best-effort event persistence. Telemetry must never break user work."""
import json
from collections import Counter
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.event import Event


class EventService:
    @staticmethod
    async def record(db: AsyncSession | None, event_type: str, *, status: str = "completed", correlation_id: str | None = None, objective_id: str | None = None, entity_type: str | None = None, entity_id: str | None = None, latency_ms: int | None = None, token_count: int | None = None, metadata: dict[str, Any] | None = None, error: str | None = None) -> None:
        if db is None:
            return
        try:
            db.add(Event(event_type=event_type, status=status, correlation_id=correlation_id, objective_id=objective_id, entity_type=entity_type, entity_id=entity_id, latency_ms=latency_ms, token_count=token_count, metadata_json=json.dumps(metadata or {}, default=str), error=(error or "")[:2000] or None))
            await db.flush()
        except Exception:
            return

    @staticmethod
    async def recent(db: AsyncSession, limit: int = 100, correlation_id: str | None = None) -> list[Event]:
        stmt = select(Event).order_by(Event.created_at.desc()).limit(min(max(limit, 1), 250))
        if correlation_id:
            stmt = stmt.where(Event.correlation_id == correlation_id)
        return list((await db.execute(stmt)).scalars())

    @staticmethod
    async def metrics(db: AsyncSession) -> dict[str, Any]:
        rows = list((await db.execute(select(Event))).scalars())
        counts = Counter(event.event_type for event in rows)
        latencies = [event.latency_ms for event in rows if event.latency_ms is not None]
        return {"total_events": len(rows), "failures": sum(event.status == "failed" for event in rows), "by_type": dict(counts), "average_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0, "token_estimate": sum(event.token_count or 0 for event in rows)}
