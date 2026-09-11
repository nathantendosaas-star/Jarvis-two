from pydantic import BaseModel, Field
from datetime import datetime

class ProjectBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = ""
    icon: str | None = "📁"
    color: str | None = "#3b82f6"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
