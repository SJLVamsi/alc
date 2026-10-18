import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.logging import logger
from app.services.llm_client import llm_client

router = APIRouter(prefix="/api/page", tags=["page"])

MAX_CONTEXT_CHARS = 12000
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 8000
MAX_HISTORY_MESSAGE_CHARS = 4000
MAX_CODE_CHARS = 15000
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
    code_context: Optional[str] = None
    code_intent: Optional[bool] = False


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _sanitize_history(history) -> list[dict]:
    """Keep only real user/assistant turns, bounded by count *and* size.

    Trimming by message count alone lets a few enormous turns blow the
    context window, so the character budget is enforced too.
    """
    clean: list[dict] = []
    for message in history or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role not in ("user", "assistant"):
            continue  # a client cannot inject a system prompt this way
        content = str(message.get("content") or "")
        if not content.strip():
            continue
        clean.append({"role": role, "content": content[:MAX_HISTORY_MESSAGE_CHARS]})

    clean = clean[-MAX_HISTORY_TURNS:]

    kept: list[dict] = []
    total = 0
    for message in reversed(clean):
        total += len(message["content"])
        if total > MAX_HISTORY_CHARS:
            break
        kept.insert(0, message)
    return kept


def _resolve_context(req: PageAskRequest) -> tuple[str, bool]:
    """Return (context, missing).

    `missing` means the caller asked us to use cached page text that is gone,
    so the extension must resend the page rather than get a contextless answer.
    """
    selection = (req.selection or "").strip()
    if selection:
        return selection[:MAX_CONTEXT_CHARS], False

    if req.page_text:
        if req.page_hash:
            _cache_put(req.page_hash, req.page_text)
        return req.page_text[:MAX_CONTEXT_CHARS], False

    if req.page_hash:
        cached = _cache_get(req.page_hash)
        if cached:
            return cached[:MAX_CONTEXT_CHARS], False
        return "", True

    return "", True


def _build_messages(req: PageAskRequest, context: str) -> list[dict]:
    system = SYSTEM_PROMPT
    if req.title:
        system += f"\n\nPage title: {req.title}"
    if context:
        system += f"\n\n--- PAGE CONTENT ---\n{context}"

    if req.code_context:
        system += (
            "\n\nThe page contains one or more numbered code blocks in the format "
            "'=== Code block N ==='. Identify the block that matches the question "
            "and keep its exact function name, parameter names and return type:\n"
            f"{req.code_context[:MAX_CODE_CHARS]}"
        )
        if req.code_intent:
            system += (
                "\n\nThe user is asking you to write code. Provide a complete, working "
                "implementation that fits the starter code above. Match the given "
                "function signature exactly and return the required type. Show the "
                "full code in a fenced block, then briefly explain how it works."
            )

    messages = [{"role": "system", "content": system}]
    messages.extend(_sanitize_history(req.history))
    messages.append({"role": "user", "content": req.question})
    return messages


@router.post("/ask")
async def page_ask(req: PageAskRequest):
    context, missing = _resolve_context(req)
    if missing and not req.code_context:
        # Tell the extension to resend the page body instead of quietly
        # answering from nothing.
        logger.info("page_ask_context_missing", url=req.url)
        raise HTTPException(status_code=409, detail="page context missing")

    messages = _build_messages(req, context)

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
