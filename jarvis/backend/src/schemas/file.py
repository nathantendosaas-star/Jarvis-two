from pydantic import BaseModel
from datetime import datetime

class FileResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    path: str
    size: int | None = 0
    mime_type: str | None = "application/octet-stream"
    created_at: datetime

    class Config:
        from_attributes = True

class WorkspaceFileNode(BaseModel):
    name: str
    path: str
    isDirectory: bool
    type: str | None = "text"
    size: int | None = 0
    modifiedAt: datetime | None = None
    content: str | None = None
    children: list["WorkspaceFileNode"] | None = None
