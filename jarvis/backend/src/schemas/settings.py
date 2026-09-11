from pydantic import BaseModel

class SettingUpdate(BaseModel):
    value: str

class SettingResponse(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True
