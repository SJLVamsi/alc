import json
from typing import Optional
from app.services.llm_client import llm_client
from app.core.logging import logger
from app.core.exceptions import LLMError


class MCQExplainer:
    async def extract_question(self, page_text: str) -> dict:
        prompt = f"""Extract the multiple choice question from this page content.

Page Content: {page_text[:6000]}

Return valid JSON with:
- question_text: the question
- options: list of {{"label": "A/B/C/D", "text": "option text"}}

If correct answer is visible, include "correct_answer": "A/B/C/D"
"""
        try:
            response = await llm_client.generate(prompt)
            return json.loads(response)
        except (LLMError, json.JSONDecodeError) as e:
            logger.error("mcq_extraction_failed", error=str(e))
            return {"question_text": page_text[:500], "options": []}

    async def explain_question(self, question_text: str, options: list[dict]) -> dict:
        options_text = "\n".join(f"{o['label']}: {o['text']}" for o in options)
        prompt = f"""Analyze this multiple choice question and provide a detailed explanation.

Question: {question_text}

Options:
{options_text}

For each option, explain whether it is correct or incorrect and why.
Then provide the suggested answer and overall reasoning.

Return valid JSON with:
- options: list of {{"label", "text", "is_correct", "explanation"}}
- suggested_answer: the correct label
- overall_reasoning: explanation of the reasoning
"""
        try:
            response = await llm_client.generate(prompt)
            return json.loads(response)
        except (LLMError, json.JSONDecodeError) as e:
            logger.error("mcq_explanation_failed", error=str(e))
            return self._fallback_explanation(question_text, options)

    def _fallback_explanation(self, question: str, options: list[dict]) -> dict:
        return {
            "options": [
                {"label": o.get("label", "?"), "text": o.get("text", ""),
                 "is_correct": False, "explanation": "Analysis unavailable"}
                for o in options
            ],
            "suggested_answer": options[0]["label"] if options else "A",
            "overall_reasoning": f"The question asks: {question[:100]}... Manual review recommended.",
        }


mcq_explainer = MCQExplainer()
