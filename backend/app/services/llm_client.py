import json
from typing import AsyncIterator, Optional

import httpx

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMError


class LLMClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.num_ctx = settings.ollama_num_ctx

    def _options(self, num_ctx: Optional[int] = None) -> dict:
        return {"num_ctx": num_ctx or self.num_ctx}

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self._options(),
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except httpx.HTTPError as e:
            logger.error("llm_request_failed", error=str(e))
            raise LLMError(f"LLM request failed: {e}") from e

    async def chat(self, messages: list[dict], num_ctx: Optional[int] = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self._options(num_ctx),
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error("llm_chat_failed", error=str(e))
            raise LLMError(f"LLM chat failed: {e}") from e

    async def chat_stream(
        self, messages: list[dict], num_ctx: Optional[int] = None
    ) -> AsyncIterator[str]:
        """Yield response text incrementally from Ollama's streaming /api/chat."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": self._options(num_ctx),
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if data.get("error"):
                            raise LLMError(str(data["error"]))
                        delta = data.get("message", {}).get("content", "")
                        if delta:
                            yield delta
                        if data.get("done"):
                            break
        except httpx.HTTPError as e:
            logger.error("llm_chat_stream_failed", error=str(e))
            raise LLMError(f"LLM chat stream failed: {e}") from e


llm_client = LLMClient()
