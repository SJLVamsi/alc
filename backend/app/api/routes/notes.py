from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.models.note import Note, RevisionQuestion
from app.schemas.note import (
    NoteCreate, NoteResponse, GenerationRequest, GenerationResponse,
    RevisionQuestionResponse,
)
from app.services.note_generator import note_generator
from app.services.knowledge_base import knowledge_base
from app.models.lesson import Lesson

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("/", response_model=List[NoteResponse])
async def list_notes(lesson_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Note)
    if lesson_id:
        q = q.filter(Note.lesson_id == lesson_id)
    return q.all()


@router.post("/", response_model=NoteResponse)
async def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    note = Note(**data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.post("/generate", response_model=GenerationResponse)
async def generate_notes(req: GenerationRequest):
    lesson = None
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == req.lesson_id).first()
    finally:
        db.close()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    content = lesson.content_text or ""
    notes = await note_generator.generate_notes(lesson.title, content)
    flashcards = await note_generator.generate_flashcards(content)
    questions = await note_generator.generate_revision_questions(content)

    db = SessionLocal()
    try:
        note = knowledge_base.save_notes(db, lesson.id, notes["summary"], notes["detailed_notes"], notes["key_concepts"])
        for q in questions:
            knowledge_base.save_revision_question(db, note.id, q["question"], q["answer"])
        knowledge_base.save_flashcards(db, lesson.id, flashcards)
    finally:
        db.close()

    return GenerationResponse(
        summary=notes["summary"],
        detailed_notes=notes["detailed_notes"],
        key_concepts=notes["key_concepts"],
        flashcards=flashcards,
        revision_questions=questions,
    )


@router.get("/{note_id}/questions", response_model=List[RevisionQuestionResponse])
async def get_revision_questions(note_id: int, db: Session = Depends(get_db)):
    return db.query(RevisionQuestion).filter(RevisionQuestion.note_id == note_id).all()
