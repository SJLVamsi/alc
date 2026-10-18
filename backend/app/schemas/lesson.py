from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LessonProgressResponse(BaseModel):
    id: int
    lesson_id: int
    completed: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    study_time_seconds: int

    model_config = {"from_attributes": True}


class LessonBase(BaseModel):
    title: str
    order: int = 0
    url: Optional[str] = None
    is_coding: bool = False
    is_mcq: bool = False


class LessonCreate(LessonBase):
    module_id: int


class LessonResponse(LessonBase):
    id: int
    module_id: int
    content_text: Optional[str] = None
    created_at: datetime
    progress: Optional[LessonProgressResponse] = None

    model_config = {"from_attributes": True}


class LessonContentResponse(BaseModel):
    title: str
    text: str
    is_coding: bool
    is_mcq: bool
