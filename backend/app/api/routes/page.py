import json
import time
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.logging import logger
from app.services.llm_client import llm_client

router = APIRouter(prefix="/api/page", tags=["page"])

MAX_CONTEXT_CHARS = 12000
MAX_HISTORY_TURNS = 6
CACHE_TTL_SECONDS = 300.0

SYSTEM_PROMPT = (
    "Answer using the page content below. If the answer isn't on the page, "
    "say so, then answer from general knowledge. Be concise. Use markdown."
)

# page_hash -> (page_text, stored_at). Lets the extension send the page once
# per page-version instead of resending 12k chars on every chat turn.
_page_cache: dict[str, tuple[str, float]] = {}


def _cache_put(page_hash: str, text: str) -> None:
    now = time.monotonic()
    _page_cache[page_hash] = (text, now)
    for key in [k for k, (_, ts) in _page_cache.items() if now - ts > CACHE_TTL_SECONDS]:
        _page_cache.pop(key, None)


def _cache_get(page_hash: str) -> str:
    entry = _page_cache.get(page_hash)
    if not entry:
        return ""
    text, ts = entry
    if time.monotonic() - ts > CACHE_TTL_SECONDS:
        _page_cache.pop(page_hash, None)
        return ""
    return text


class PageAskRequest(BaseModel):
    question: str
    page_text: Optional[str] = None
    page_hash: Optional[str] = None
    selection: Optional[str] = None
    history: Optional[list] = None
    title: Optional[str] = None
    url: Optional[str] = None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _build_messages(req: PageAskRequest) -> list[dict]:
    selection = (req.selection or "").strip()
    if req.page_text:
        if req.page_hash:
            _cache_put(req.page_hash, req.page_text)
        context = req.page_text
    elif req.page_hash:
        context = _cache_get(req.page_hash)
    else:
        context = ""

    context = (selection or context)[:MAX_CONTEXT_CHARS]

    history = [m for m in (req.history or []) if isinstance(m, dict)][-MAX_HISTORY_TURNS:]

    system = SYSTEM_PROMPT
    if req.title:
        system += f"\n\nPage title: {req.title}"
    if context:
        system += f"\n\n--- PAGE CONTENT ---\n{context}"

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": req.question})
    return messages


@router.post("/ask")
async def page_ask(req: PageAskRequest):
    messages = _build_messages(req)

    async def event_stream():
        try:
            async for delta in llm_client.chat_stream(messages):
                yield _sse({"delta": delta})
        except Exception as e:  # noqa: BLE001 - surface any failure to the client
            logger.error("page_ask_failed", error=str(e), url=req.url)
            yield _sse({"error": str(e)})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
