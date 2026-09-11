"""Bounded prompt context assembly with optional project-memory enrichment."""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from .memory import MemoryService


class ContextService:
    MAX_MEMORY_CHARS = 5000

    @classmethod
    async def assemble(cls, objective: str, db: AsyncSession | None, project_id: str | None = None) -> tuple[str, dict[str, Any]]:
        trace: dict[str, Any] = {"memory_count": 0, "memory_chars": 0, "degraded": False}
        if not db or not project_id:
            return objective, trace
        try:
            memories = await MemoryService.retrieve(db, project_id, objective, limit=8)
            excerpts, used = [], 0
            for memory in memories:
                excerpt = f"[{memory.memory_type}] {memory.title or 'Memory'}: {memory.content}"
                if used + len(excerpt) > cls.MAX_MEMORY_CHARS:
                    break
                excerpts.append(excerpt); used += len(excerpt)
            trace.update(memory_count=len(excerpts), memory_chars=used)
            if excerpts:
                return f"{objective}\n\nRelevant JARVIS memory:\n" + "\n".join(excerpts), trace
        except Exception:
            trace["degraded"] = True
        return objective, trace
