from pydantic import BaseModel, Field
from datetime import datetime

class MemoryBase(BaseModel):
    project_id: str
    title: str | None = ""
    content: str | None = ""
    importance: int | None = Field(5, ge=1, le=10)

class MemoryCreate(MemoryBase):
    pass

class MemoryResponse(MemoryBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
