import json
from typing import Optional
from app.services.llm_client import llm_client
from app.core.logging import logger
from app.core.exceptions import LLMError


class NoteGenerator:
    async def generate_notes(self, lesson_title: str, lesson_text: str) -> dict:
        prompt = f"""Analyze the following lesson content and generate structured learning materials.

Lesson Title: {lesson_title}
Lesson Content: {lesson_text[:8000]}

Generate:
1. CONCISE_SUMMARY: A 3-5 sentence summary.
2. DETAILED_NOTES: Comprehensive notes covering all key points.
3. KEY_CONCEPTS: List of 5-10 key concepts as a comma-separated list.

Return valid JSON with keys: summary, detailed_notes, key_concepts
"""
        try:
            response = await llm_client.generate(prompt)
            return self._parse_response(response, lesson_title, lesson_text)
        except LLMError as e:
            logger.error("note_generation_failed", error=str(e))
            return self._fallback_notes(lesson_title, lesson_text)

    async def generate_revision_questions(self, lesson_text: str, count: int = 5) -> list[dict]:
        prompt = f"""Based on this lesson content, generate {count} revision questions with answers.

Content: {lesson_text[:6000]}

Return valid JSON as a list of {{"question": "...", "answer": "..."}} objects.
"""
        try:
            response = await llm_client.generate(prompt)
            questions = json.loads(response)
            if isinstance(questions, list):
                return questions[:count]
            return []
        except (LLMError, json.JSONDecodeError) as e:
            logger.error("revision_questions_failed", error=str(e))
            return []

    async def generate_flashcards(self, lesson_text: str, count: int = 10) -> list[dict]:
        prompt = f"""Based on this lesson content, create {count} flashcards for spaced repetition.

Content: {lesson_text[:6000]}

Return valid JSON as a list of {{"front": "...", "back": "..."}} objects.
"""
        try:
            response = await llm_client.generate(prompt)
            flashcards = json.loads(response)
            if isinstance(flashcards, list):
                return flashcards[:count]
            return []
        except (LLMError, json.JSONDecodeError) as e:
            logger.error("flashcard_generation_failed", error=str(e))
            return []

    def _parse_response(self, response: str, title: str, text: str) -> dict:
        try:
            data = json.loads(response)
            return {
                "summary": data.get("summary", ""),
                "detailed_notes": data.get("detailed_notes", ""),
                "key_concepts": data.get("key_concepts", ""),
            }
        except json.JSONDecodeError:
            return self._fallback_notes(title, text)

    def _fallback_notes(self, title: str, text: str) -> dict:
        words = text.split()
        summary = " ".join(words[:100]) + ("..." if len(words) > 100 else "")
        return {
            "summary": summary or f"Notes for {title}",
            "detailed_notes": text[:5000] if text else "",
            "key_concepts": "See detailed notes",
        }


note_generator = NoteGenerator()
