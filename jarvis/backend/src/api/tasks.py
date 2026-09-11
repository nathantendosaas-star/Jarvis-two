from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..schemas.task import TaskCreate, TaskUpdate, TaskResponse
from ..services.task import TaskService
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await TaskService.create_task(db, data)

@router.get("/{project_id}", response_model=List[TaskResponse])
async def get_tasks(project_id: str, db: AsyncSession = Depends(get_db)):
    return await TaskService.get_tasks(db, project_id)

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await TaskService.update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
