from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.flashcard import Flashcard, FlashcardReview


class FlashcardService:
    SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30, 60, 120]

    def calculate_next_review(self, score: int, current_interval: int = 1) -> int:
        idx = min(score, len(self.SPACED_REPETITION_INTERVALS) - 1)
        return self.SPACED_REPETITION_INTERVALS[idx]

    def get_due_flashcards(self, db: Session, limit: int = 20) -> list[Flashcard]:
        cutoff = datetime.now(timezone.utc)
        flashcards = (
            db.query(Flashcard)
            .outerjoin(FlashcardReview)
            .group_by(Flashcard.id)
            .having(
                db.query(FlashcardReview)
                .filter(FlashcardReview.flashcard_id == Flashcard.id)
                .order_by(FlashcardReview.reviewed_at.desc())
                .limit(1)
                .subquery()
                .c.reviewed_at == None
            )
            .limit(limit)
            .all()
        )
        return flashcards

    def record_review(self, db: Session, flashcard_id: int, score: int) -> FlashcardReview:
        review = FlashcardReview(flashcard_id=flashcard_id, score=score)
        db.add(review)

        fc = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if fc:
            fc.difficulty = max(0.0, min(1.0, fc.difficulty + (0.5 - score) * 0.1))

        db.commit()
        db.refresh(review)
        return review


flashcard_service = FlashcardService()
