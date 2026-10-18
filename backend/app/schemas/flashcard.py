from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FlashcardBase(BaseModel):
    front: str
    back: str


class FlashcardCreate(FlashcardBase):
    lesson_id: int


class FlashcardResponse(FlashcardBase):
    id: int
    lesson_id: int
    difficulty: float
    created_at: datetime

    model_config = {"from_attributes": True}


class FlashcardReviewCreate(BaseModel):
    score: int


class FlashcardReviewResponse(BaseModel):
    id: int
    flashcard_id: int
    score: int
    reviewed_at: datetime

    model_config = {"from_attributes": True}


class FlashcardStats(BaseModel):
    total: int
    reviewed: int
    avg_difficulty: float
    due_for_review: int
