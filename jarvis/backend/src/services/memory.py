import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.memory import Memory
from ..schemas.memory import MemoryCreate

class MemoryService:
    @staticmethod
    async def create_memory(db: AsyncSession, data: MemoryCreate) -> Memory:
        memory = Memory(
            id=str(uuid.uuid4()),
            project_id=data.project_id,
            title=data.title,
            content=data.content,
            importance=data.importance
        )
        db.add(memory)
        await db.flush()
        return memory

    @staticmethod
    async def get_memories(db: AsyncSession, project_id: str) -> List[Memory]:
        result = await db.execute(select(Memory).where(Memory.project_id == project_id))
        return list(result.scalars().all())

    @staticmethod
    async def delete_memory(db: AsyncSession, memory_id: str) -> bool:
        memory = await db.get(Memory, memory_id)
        if not memory:
            return False
        await db.delete(memory)
        await db.flush()
        return True
