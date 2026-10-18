from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.models.analytics import StudySession, WeakArea
from app.schemas.analytics import DashboardStats, StudySessionResponse, WeakAreaResponse
from app.services.knowledge_base import knowledge_base

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: Session = Depends(get_db)):
    return knowledge_base.get_dashboard_stats(db)


@router.get("/sessions", response_model=List[StudySessionResponse])
async def get_sessions(db: Session = Depends(get_db)):
    return db.query(StudySession).order_by(StudySession.started_at.desc()).limit(50).all()


@router.get("/weak-areas", response_model=List[WeakAreaResponse])
async def get_weak_areas(db: Session = Depends(get_db)):
    return db.query(WeakArea).order_by(WeakArea.confidence).all()
