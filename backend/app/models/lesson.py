from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)
    url = Column(String, nullable=True)
    content_text = Column(Text, nullable=True)
    is_coding = Column(Boolean, default=False)
    is_mcq = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    module = relationship("Module", back_populates="lessons")
    progress = relationship("LessonProgress", uselist=False, back_populates="lesson", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="lesson", cascade="all, delete-orphan")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, unique=True)
    completed = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    study_time_seconds = Column(Integer, default=0)

    lesson = relationship("Lesson", back_populates="progress")
