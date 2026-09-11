from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..schemas.file import FileResponse, WorkspaceFileNode
from ..services.file import FileService
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await FileService.save_file(db, project_id, file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )

@router.get("/workspace/tree", response_model=List[WorkspaceFileNode])
async def get_workspace_tree():
    return FileService.get_workspace_tree()

@router.get("/{project_id}", response_model=List[FileResponse])
async def get_files(project_id: str, db: AsyncSession = Depends(get_db)):
    return await FileService.get_files(db, project_id)

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    success = await FileService.delete_file(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File metadata not found")
    return None
