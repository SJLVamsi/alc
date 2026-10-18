from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DashboardStats(BaseModel):
    lessons_completed: int
    total_lessons: int
    study_time_minutes: float
    concepts_learned: int
    weak_areas: list[str]
    flashcards_due: int
    next_revision: Optional[str] = None


class StudySessionResponse(BaseModel):
    id: int
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    duration_seconds: int
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WeakAreaResponse(BaseModel):
    id: int
    concept: str
    confidence: float
    last_reviewed: Optional[datetime] = None

    model_config = {"from_attributes": True}
