from pydantic import BaseModel, Field
from datetime import datetime

class MessageBase(BaseModel):
    role: str = Field(..., description="'user' or 'model'")
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    chat_id: str
    token_count: int | None = 0
    latency: float | None = 0.0
    created_at: datetime

    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    project_id: str
    title: str | None = "New Chat"

class ChatCreate(ChatBase):
    pass

class ChatResponse(ChatBase):
    id: str
    summary: str | None = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StreamRequest(BaseModel):
    chat_id: str
    message: str
    systemInstruction: str | None = None
    model: str | None = "gemini-3.1-flash-lite"
    useSearch: bool | None = False
