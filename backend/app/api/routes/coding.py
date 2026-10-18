from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.models.coding import CodingProblem, CodingSolution, CodingHint
from app.schemas.coding import (
    CodingProblemResponse, CodingHintResponse, CodingSolutionCreate,
    CodingSolutionResponse, ProblemExplanation,
)
from app.services.coding_assistant import coding_assistant

router = APIRouter(prefix="/api/coding", tags=["coding"])


@router.get("/problems", response_model=List[CodingProblemResponse])
async def list_problems(lesson_id: int = None, db: Session = Depends(get_db)):
    q = db.query(CodingProblem)
    if lesson_id:
        q = q.filter(CodingProblem.lesson_id == lesson_id)
    return q.all()


@router.post("/explain")
async def explain_problem(problem_statement: str = Query(..., min_length=1)):
    result = await coding_assistant.explain_problem(problem_statement)
    return result


@router.get("/problems/{problem_id}/hints", response_model=List[CodingHintResponse])
async def get_hints(problem_id: int, db: Session = Depends(get_db)):
    return db.query(CodingHint).filter(CodingHint.problem_id == problem_id).order_by(CodingHint.level).all()


@router.post("/problems/{problem_id}/hints/generate")
async def generate_hint(problem_id: int, level: int = Query(1, ge=1, le=5), db: Session = Depends(get_db)):
    problem = db.query(CodingProblem).filter(CodingProblem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    hint_text = await coding_assistant.generate_hints(problem.description, level)
    hint = CodingHint(problem_id=problem_id, level=level, content=hint_text)
    db.add(hint)
    db.commit()
    db.refresh(hint)
    return hint


@router.post("/problems/{problem_id}/review", response_model=CodingSolutionResponse)
async def review_solution(problem_id: int, data: CodingSolutionCreate, db: Session = Depends(get_db)):
    problem = db.query(CodingProblem).filter(CodingProblem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    review = await coding_assistant.review_solution(problem.description, data.user_code, data.language)
    solution = CodingSolution(
        problem_id=problem_id,
        user_code=data.user_code,
        language=data.language,
        time_complexity=review.get("time_complexity"),
        space_complexity=review.get("space_complexity"),
        feedback=review.get("feedback"),
        is_optimal=review.get("is_optimal", False),
    )
    db.add(solution)
    db.commit()
    db.refresh(solution)
    return solution
