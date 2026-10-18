from fastapi import APIRouter, HTTPException, Query
from app.services.mcq_explainer import mcq_explainer
from app.schemas.mcq import MCQExplanationResponse, MCQExtractedResponse

router = APIRouter(prefix="/api/mcq", tags=["mcq"])


@router.post("/extract", response_model=MCQExtractedResponse)
async def extract_question(page_text: str = Query(..., min_length=1)):
    result = await mcq_explainer.extract_question(page_text)
    return MCQExtractedResponse(
        question_text=result.get("question_text", ""),
        options=result.get("options", []),
    )


@router.post("/explain", response_model=MCQExplanationResponse)
async def explain_mcq(question_text: str = Query(..., min_length=1), options_json: str = Query("[]")):
    import json
    try:
        options = json.loads(options_json)
    except json.JSONDecodeError:
        options = []
    result = await mcq_explainer.explain_question(question_text, options)
    return MCQExplanationResponse(
        question_text=question_text,
        options=result.get("options", []),
        suggested_answer=result.get("suggested_answer", ""),
        overall_reasoning=result.get("overall_reasoning", ""),
    )
