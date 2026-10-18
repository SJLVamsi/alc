from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.models.lesson import Lesson, LessonProgress
from app.schemas.lesson import LessonCreate, LessonResponse, LessonProgressResponse

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/", response_model=List[LessonResponse])
async def list_lessons(module_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Lesson)
    if module_id:
        q = q.filter(Lesson.module_id == module_id)
    return q.all()


@router.post("/", response_model=LessonResponse)
async def create_lesson(data: LessonCreate, db: Session = Depends(get_db)):
    lesson = Lesson(**data.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.post("/{lesson_id}/progress", response_model=LessonProgressResponse)
async def update_progress(lesson_id: int, completed: bool = True, db: Session = Depends(get_db)):
    progress = db.query(LessonProgress).filter(LessonProgress.lesson_id == lesson_id).first()
    if not progress:
        progress = LessonProgress(lesson_id=lesson_id, completed=completed)
        db.add(progress)
    else:
        progress.completed = completed
    db.commit()
    db.refresh(progress)
    return progress
