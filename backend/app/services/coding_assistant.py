from typing import Optional
from app.services.llm_client import llm_client
from app.core.logging import logger
from app.core.exceptions import LLMError


class CodingAssistant:
    async def explain_problem(self, problem_statement: str) -> dict:
        prompt = f"""Analyze this coding problem and provide a detailed explanation.

Problem: {problem_statement}

Provide:
1. explanation: A clear explanation of what the problem is asking
2. algorithms: List of algorithms that could be used
3. data_structures: List of relevant data structures
4. approach: A step-by-step approach to solve it

Return valid JSON with keys: explanation, algorithms, data_structures, approach
"""
        try:
            response = await llm_client.generate(prompt)
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return self._fallback_explanation(problem_statement)
        except LLMError as e:
            logger.error("coding_explain_failed", error=str(e))
            return self._fallback_explanation(problem_statement)

    async def generate_hints(self, problem_statement: str, level: int = 1) -> str:
        prompt = f"""For this coding problem, provide a hint at difficulty level {level} (1=easy, 5=hard).

Problem: {problem_statement}

Give a single, specific hint that guides without giving away the full solution.
"""
        try:
            return await llm_client.generate(prompt)
        except LLMError as e:
            logger.error("hint_generation_failed", error=str(e))
            return "Break the problem into smaller subproblems and solve each one."

    async def review_solution(
        self, problem_statement: str, user_code: str, language: str = "python"
    ) -> dict:
        prompt = f"""Review this coding solution and provide feedback.

Problem: {problem_statement}

Solution ({language}):
```
{user_code}
```

Provide:
1. feedback: Constructive feedback on the solution
2. time_complexity: Big-O time complexity analysis
3. space_complexity: Big-O space complexity analysis
4. is_optimal: boolean indicating if this is optimal

Return valid JSON.
"""
        try:
            response = await llm_client.generate(prompt)
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return self._fallback_review()
        except LLMError as e:
            logger.error("solution_review_failed", error=str(e))
            return self._fallback_review()

    def _fallback_explanation(self, problem: str) -> dict:
        return {
            "explanation": f"This problem asks: {problem[:200]}...",
            "algorithms": ["Divide and Conquer", "Dynamic Programming"],
            "data_structures": ["Arrays", "Hash Maps"],
            "approach": "Analyze the input, choose appropriate data structures, implement the algorithm, test edge cases.",
        }

    def _fallback_review(self) -> dict:
        return {
            "feedback": "Solution submitted for review.",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "is_optimal": False,
        }

    async def extract_problem(self, page_text: str) -> dict:
        prompt = f"""Extract the coding problem from this page content.

Page Content: {page_text[:6000]}

Return valid JSON with keys: title, description, solution_template (if any)
"""
        try:
            response = await llm_client.generate(prompt)
            import json
            return json.loads(response)
        except (LLMError, json.JSONDecodeError) as e:
            logger.error("problem_extraction_failed", error=str(e))
            return {"title": "Unknown Problem", "description": page_text[:1000], "solution_template": ""}


coding_assistant = CodingAssistant()
