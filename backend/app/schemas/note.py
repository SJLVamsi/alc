from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NoteBase(BaseModel):
    summary: Optional[str] = None
    detailed_notes: Optional[str] = None
    key_concepts: Optional[str] = None


class NoteCreate(NoteBase):
    lesson_id: int


class NoteResponse(NoteBase):
    id: int
    lesson_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RevisionQuestionResponse(BaseModel):
    id: int
    note_id: int
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerationRequest(BaseModel):
    lesson_id: int


class GenerationResponse(BaseModel):
    summary: str
    detailed_notes: str
    key_concepts: str
    flashcards: list[dict]
    revision_questions: list[dict]
