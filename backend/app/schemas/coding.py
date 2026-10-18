from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CodingProblemResponse(BaseModel):
    id: int
    lesson_id: int
    title: str
    description: str
    solution_template: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CodingHintResponse(BaseModel):
    id: int
    level: int
    content: str

    model_config = {"from_attributes": True}


class CodingSolutionCreate(BaseModel):
    problem_id: int
    user_code: str
    language: str = "python"


class CodingSolutionResponse(BaseModel):
    id: int
    problem_id: int
    user_code: str
    language: str
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    feedback: Optional[str] = None
    is_optimal: bool
    submitted_at: datetime

    model_config = {"from_attributes": True}


class ProblemExplanation(BaseModel):
    problem_statement: str
    explanation: str
    algorithms: list[str]
    data_structures: list[str]
    approach: str
