from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ModuleBase(BaseModel):
    name: str
    order: int = 0
    url: Optional[str] = None


class ModuleCreate(ModuleBase):
    pass


class ModuleResponse(ModuleBase):
    id: int
    course_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseBase(BaseModel):
    name: str
    platform: Optional[str] = None
    url: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class CourseResponse(CourseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    modules: list[ModuleResponse] = []

    model_config = {"from_attributes": True}
