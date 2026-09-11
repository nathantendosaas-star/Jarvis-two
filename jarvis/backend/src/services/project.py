import uuid
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.project import Project
from ..schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    @staticmethod
    async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            icon=data.icon,
            color=data.color
        )
        db.add(project)
        await db.flush()
        return project

    @staticmethod
    async def get_projects(db: AsyncSession) -> List[Project]:
        result = await db.execute(select(Project).order_by(desc(Project.updated_at)))
        return list(result.scalars().all())

    @staticmethod
    async def get_project(db: AsyncSession, project_id: str) -> Optional[Project]:
        return await db.get(Project, project_id)

    @staticmethod
    async def update_project(db: AsyncSession, project_id: str, data: ProjectUpdate) -> Optional[Project]:
        project = await db.get(Project, project_id)
        if not project:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
            
        await db.flush()
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: str) -> bool:
        project = await db.get(Project, project_id)
        if not project:
            return False
        await db.delete(project)
        await db.flush()
        return True
