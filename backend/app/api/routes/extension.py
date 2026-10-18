from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.llm_client import llm_client
from app.services.coding_assistant import coding_assistant
from app.services.mcq_explainer import mcq_explainer
from app.core.logging import logger
from app.core.exceptions import LLMError

router = APIRouter(prefix="/api/extension", tags=["extension"])


class ExtensionRequest(BaseModel):
    action: str
    text: Optional[str] = None
    title: Optional[str] = None
    messages: Optional[list] = None
    context: Optional[str] = None
    page_context: Optional[str] = None
    options: Optional[list[str]] = None
    code_context: Optional[str] = None
    code_intent: Optional[bool] = False


@router.post("/ask")
async def extension_ask(req: ExtensionRequest):
    try:
        if req.action == "explain":
            text = (req.text or req.context or "")[:4000]
            prompt = f"""Explain the following concept in simple terms for a student.

Content: {text}

Provide a clear, concise explanation with examples where helpful."""
            response = await llm_client.generate(prompt)
            return {"response": response}

        elif req.action == "coding-help":
            text = (req.text or "")[:4000]
            if req.code_context:
                prompt = (
                    "You are helping a student on a coding platform. The page shows coding "
                    "problems with starter code or pre-filled solution templates. The code is "
                    "provided as numbered blocks ('=== Code block N ==='). Use the block that "
                    "matches this problem. "
                    "Write a complete, working solution that matches the starter code exactly: "
                    "keep the function name, parameter names, and return type, and use the "
                    "already-defined variables. First give the full code in a code block, then "
                    "briefly explain the approach.\n\n"
                    f"Problem: {text}\n\nCode blocks on the page:\n{req.code_context[:15000]}"
                )
                resp = await llm_client.generate(prompt)
                return {"response": resp}
            result = await coding_assistant.explain_problem(text)
            if not result.get("explanation"):
                prompt = (
                    "Explain this coding problem and how to approach it. "
                    "If starter code or a function signature is provided, write the complete "
                    "implementation using exactly the given function name, parameter names, "
                    "and return type:\n\n"
                    f"{text}"
                )
                resp = await llm_client.generate(prompt)
                return {"response": resp}
            return result

        elif req.action == "mcq-explain":
            # The explainer owns the whole decision: supplied options, then
            # regex over the captured region, then a bounded model call.
            result = await mcq_explainer.extract_question(
                page_text=(req.context or req.text or "")[:6000],
                question_text=(req.text or "")[:2000],
                options=req.options,
            )
            explanation = await mcq_explainer.explain_question(
                result["question_text"], result["options"]
            )
            return {
                "question_text": result["question_text"],
                "options": explanation.get("options", []),
                "suggested_answer": explanation.get("suggested_answer", ""),
                "overall_reasoning": explanation.get("overall_reasoning", ""),
                "capture_source": result.get("source", ""),
            }

        elif req.action == "generate-notes":
            text = (req.context or req.text or "")[:6000]
            prompt = f"""Analyze this learning content and generate structured notes.

Title: {req.title or 'Untitled'}
Content: {text}

Generate:
1. SUMMARY: 3-5 sentence summary
2. KEY_CONCEPTS: Comma-separated list of key concepts
3. FLASHCARDS: 5 question-answer pairs as Q1: ... A1: ... format
"""
            response = await llm_client.generate(prompt)
            return {"response": response}

        elif req.action == "chat":
            messages = req.messages or []
            if not messages:
                messages = [{"role": "user", "content": req.text or "Hello"}]

            system_msg = ""
            if req.page_context:
                context = (req.page_context or "")[:12000]
                system_msg = (
                    "You are a student's learning assistant embedded on their course page. "
                    "Use the page content below to answer questions. If the question is not about "
                    "the page, answer it directly.\n\n"
                    f"Current page content:\n{context}"
                )

            if req.code_context:
                system_msg = (system_msg or "") + (
                    "\n\nThe page contains one or more numbered code blocks in the format "
                    "'=== Code block N ==='. Identify the code block that matches the question "
                    "the user is asking about and answer for that one. Use it as-is: "
                    "keep the exact function name, parameter names, and return type:\n"
                    f"{req.code_context[:15000]}"
                )
                if req.code_intent:
                    system_msg += (
                        "\n\nThe user is asking you to write code. Provide a complete, working "
                        "implementation that fits the starter code above. Match the given function "
                        "signature exactly, use the given parameter names, and return the required "
                        "type. Show the full code in a code block, then briefly explain how it works."
                    )

            if system_msg:
                messages = [{"role": "system", "content": system_msg}] + messages

            response = await llm_client.chat(messages)
            return {"response": response}

        elif req.action == "quick-ask":
            prompt = f"""Question: {req.text}

Provide a clear, concise explanation suitable for a student. Use examples if helpful."""
            response = await llm_client.generate(prompt)
            return {"response": response}

        else:
            return {"error": f"Unknown action: {req.action}"}

    except LLMError as e:
        logger.error("extension_llm_failed", action=req.action, error=str(e))
        raise HTTPException(status_code=502, detail="Model failed, retry")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("extension_request_failed", action=req.action, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
