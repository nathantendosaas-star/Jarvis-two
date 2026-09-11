import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.task import Task
from ..schemas.task import TaskCreate, TaskUpdate
from ..core.events import event_broker

class TaskService:
    @staticmethod
    async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            project_id=data.project_id,
            chat_id=data.chat_id,
            title=data.title,
            description=data.description,
            status="queued"
        )
        db.add(task)
        await db.flush()
        
        # Publish event
        await event_broker.publish("TaskCreated", {"task_id": task.id, "project_id": task.project_id})
        return task

    @staticmethod
    async def get_tasks(db: AsyncSession, project_id: str) -> List[Task]:
        result = await db.execute(select(Task).where(Task.project_id == project_id))
        return list(result.scalars().all())

    @staticmethod
    async def update_task(db: AsyncSession, task_id: str, data: TaskUpdate) -> Optional[Task]:
        task = await db.get(Task, task_id)
        if not task:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        
        # Automatically handle starting and finishing timestamps based on status
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == "running" and not task.started_at:
                task.started_at = datetime.now(timezone.utc)
            elif new_status in ["completed", "failed", "cancelled"] and not task.finished_at:
                task.finished_at = datetime.now(timezone.utc)
                
        for key, value in update_data.items():
            setattr(task, key, value)
            
        await db.flush()
        
        # Publish event
        await event_broker.publish("TaskUpdated", {
            "task_id": task.id,
            "project_id": task.project_id,
            "status": task.status
        })
        return task
