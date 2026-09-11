import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..services.events import EventService

router = APIRouter()

@router.get("/")
async def recent_events(limit: int = Query(100, ge=1, le=250), correlation_id: str | None = None, db: AsyncSession = Depends(get_db)):
    rows = await EventService.recent(db, limit, correlation_id)
    return [{"id": e.id, "type": e.event_type, "status": e.status, "correlation_id": e.correlation_id, "objective_id": e.objective_id, "entity_type": e.entity_type, "entity_id": e.entity_id, "latency_ms": e.latency_ms, "token_count": e.token_count, "metadata": json.loads(e.metadata_json or "{}"), "error": e.error, "created_at": e.created_at} for e in rows]

@router.get("/metrics")
async def event_metrics(db: AsyncSession = Depends(get_db)):
    return await EventService.metrics(db)
