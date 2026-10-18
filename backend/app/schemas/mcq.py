from pydantic import BaseModel
from typing import Optional


class MCQOptionExplanation(BaseModel):
    label: str
    text: str
    is_correct: bool
    explanation: str


class MCQExplanationResponse(BaseModel):
    question_text: str
    options: list[MCQOptionExplanation]
    suggested_answer: str
    overall_reasoning: str


class MCQExtractedResponse(BaseModel):
    question_text: str
    options: list[dict]
