"""Pydantic schemas for the Job model."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    script_path: str
    output_path: Optional[str] = None
    status: str
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    stdout_log: Optional[str] = None
    stderr_log: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: Optional[int] = None


class JobCompleteRequest(BaseModel):
    output_path: str
    row_count: Optional[int] = None
