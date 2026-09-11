"""Pydantic schemas for the Agent model — request validation and response serialization."""

import json
from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Any


class AgentBase(BaseModel):
    name: str
    role: str = "General Agent"
    avatar: str = "🤖"
    status: str = "idle"
    current_task: str | None = None
    priority: str = "medium"
    cpu_allocation: int = Field(50, ge=0, le=100)
    memory_allocation: int = Field(128, ge=0, le=512)
    capabilities: list[str] = []
    tools: list[str] = []
    activity: list[str] = []
    performance: int = Field(100, ge=0, le=100)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    avatar: str | None = None
    status: str | None = None
    current_task: str | None = None
    priority: str | None = None
    cpu_allocation: int | None = Field(None, ge=0, le=100)
    memory_allocation: int | None = Field(None, ge=0, le=512)
    capabilities: list[str] | None = None
    tools: list[str] | None = None
    activity: list[str] | None = None
    performance: int | None = Field(None, ge=0, le=100)


class AgentResponse(AgentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, values: Any) -> Any:
        """Convert JSON-encoded Text columns back to Python lists before validation."""
        if hasattr(values, "__dict__"):
            # Construct a dictionary from the ORM object to avoid mutating it in-place
            obj = values
            res = {}
            # Copy all fields from the object
            for k in (
                "id", "name", "role", "avatar", "status", "current_task", 
                "priority", "cpu_allocation", "memory_allocation", 
                "capabilities", "tools", "activity", "performance", 
                "created_at", "updated_at"
            ):
                val = getattr(obj, k, None)
                if k in ("capabilities", "tools", "activity") and isinstance(val, str):
                    try:
                        res[k] = json.loads(val)
                    except (json.JSONDecodeError, ValueError):
                        res[k] = []
                else:
                    res[k] = val
            return res

        if isinstance(values, dict):
            for field in ("capabilities", "tools", "activity"):
                raw = values.get(field)
                if isinstance(raw, str):
                    try:
                        values[field] = json.loads(raw)
                    except (json.JSONDecodeError, ValueError):
                        values[field] = []
        return values
