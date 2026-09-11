from pydantic import BaseModel
from datetime import datetime

class TaskBase(BaseModel):
    project_id: str
    title: str
    description: str | None = ""

class TaskCreate(TaskBase):
    chat_id: str | None = None

class TaskUpdate(BaseModel):
    status: str | None = None
    description: str | None = None
    logs: str | None = None
    finished_at: datetime | None = None

class TaskResponse(TaskBase):
    id: str
    chat_id: str | None = None
    status: str
    logs: str | None = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Config:
        from_attributes = True
