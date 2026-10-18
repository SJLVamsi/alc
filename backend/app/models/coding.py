from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    solution_template = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson")
    hints = relationship("CodingHint", back_populates="problem", cascade="all, delete-orphan")
    solutions = relationship("CodingSolution", back_populates="problem", cascade="all, delete-orphan")


class CodingHint(Base):
    __tablename__ = "coding_hints"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("coding_problems.id"), nullable=False)
    level = Column(Integer, default=1)
    content = Column(Text, nullable=False)

    problem = relationship("CodingProblem", back_populates="hints")


class CodingSolution(Base):
    __tablename__ = "coding_solutions"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("coding_problems.id"), nullable=False)
    user_code = Column(Text, nullable=False)
    language = Column(String, default="python")
    is_optimal = Column(Boolean, default=False)
    time_complexity = Column(String, nullable=True)
    space_complexity = Column(String, nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    problem = relationship("CodingProblem", back_populates="solutions")
