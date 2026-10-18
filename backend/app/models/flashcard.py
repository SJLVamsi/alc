from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    difficulty = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson")
    reviews = relationship("FlashcardReview", back_populates="flashcard", cascade="all, delete-orphan")


class FlashcardReview(Base):
    __tablename__ = "flashcard_reviews"

    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    score = Column(Integer, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())

    flashcard = relationship("Flashcard", back_populates="reviews")
