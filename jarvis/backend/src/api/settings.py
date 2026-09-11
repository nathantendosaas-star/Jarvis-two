from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models.settings import Setting
from ..schemas.settings import SettingUpdate, SettingResponse
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/")
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    settings_list = result.scalars().all()
    return {s.key: s.value for s in settings_list}

@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    setting = await db.get(Setting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.patch("/{key}", response_model=SettingResponse)
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    setting = await db.get(Setting, key)
    if not setting:
        setting = Setting(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
    await db.flush()
    return setting
