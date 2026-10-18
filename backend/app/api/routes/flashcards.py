from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.models.flashcard import Flashcard, FlashcardReview
from app.schemas.flashcard import (
    FlashcardCreate, FlashcardResponse, FlashcardReviewCreate,
    FlashcardReviewResponse, FlashcardStats,
)
from app.services.flashcard_generator import flashcard_service

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


@router.get("/", response_model=List[FlashcardResponse])
async def list_flashcards(lesson_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Flashcard)
    if lesson_id:
        q = q.filter(Flashcard.lesson_id == lesson_id)
    return q.all()


@router.post("/", response_model=FlashcardResponse)
async def create_flashcard(data: FlashcardCreate, db: Session = Depends(get_db)):
    fc = Flashcard(**data.model_dump())
    db.add(fc)
    db.commit()
    db.refresh(fc)
    return fc


@router.get("/due", response_model=List[FlashcardResponse])
async def get_due_flashcards(db: Session = Depends(get_db)):
    return flashcard_service.get_due_flashcards(db)


@router.post("/{flashcard_id}/review", response_model=FlashcardReviewResponse)
async def review_flashcard(flashcard_id: int, data: FlashcardReviewCreate, db: Session = Depends(get_db)):
    fc = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    return flashcard_service.record_review(db, flashcard_id, data.score)


@router.get("/stats", response_model=FlashcardStats)
async def get_flashcard_stats(db: Session = Depends(get_db)):
    total = db.query(Flashcard).count()
    reviewed = db.query(FlashcardReview.flashcard_id).distinct().count()
    diffs = [r[0] for r in db.query(Flashcard.difficulty).all() if r[0] is not None]
    avg = sum(diffs) / len(diffs) if diffs else 0.0
    return FlashcardStats(
        total=total,
        reviewed=reviewed,
        avg_difficulty=avg,
        due_for_review=total - reviewed,
    )
