from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MCQQuestion(Base):
    __tablename__ = "mcq_questions"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    correct_answer = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson")
    options = relationship("MCQOption", back_populates="question", cascade="all, delete-orphan")


class MCQOption(Base):
    __tablename__ = "mcq_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("mcq_questions.id"), nullable=False)
    label = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    explanation = Column(Text, nullable=True)

    question = relationship("MCQQuestion", back_populates="options")
