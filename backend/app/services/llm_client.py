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
        self.temperature = settings.ollama_temperature

    def _payload(
        self,
        messages: list[dict],
        *,
        stream: bool,
        num_ctx: Optional[int] = None,
        json_mode: bool = False,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": num_ctx or self.num_ctx,
                "temperature": self.temperature,
            },
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    async def _complete(
        self,
        messages: list[dict],
        num_ctx: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        payload = self._payload(messages, stream=False, num_ctx=num_ctx, json_mode=json_mode)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error("llm_chat_failed", error=str(e))
            raise LLMError(f"LLM chat failed: {e}") from e

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Single-shot completion. Kept as the callers' entry point; it now
        goes through /api/chat so every request carries the same options."""
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self._complete(messages, json_mode=json_mode)

    async def chat(
        self,
        messages: list[dict],
        num_ctx: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        return await self._complete(messages, num_ctx=num_ctx, json_mode=json_mode)

    async def chat_stream(
        self,
        messages: list[dict],
        num_ctx: Optional[int] = None,
        json_mode: bool = False,
    ) -> AsyncIterator[str]:
        """Yield response text incrementally from Ollama's streaming /api/chat."""
        payload = self._payload(messages, stream=True, num_ctx=num_ctx, json_mode=json_mode)
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
