"""Lenient parsing of model JSON, with a single strict retry.

Models wrap JSON in prose or code fences even when told not to. We salvage
that, but we never paper over a failure by inventing a value: if the model
cannot produce usable JSON twice, the caller gets an LLMError and the UI
says so.
"""
import json
import re
from typing import Iterable, Optional

from app.core.exceptions import LLMError
from app.core.logging import logger
from app.services.llm_client import llm_client

FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)
RETRY_INSTRUCTION = "Return ONLY valid JSON."


class JSONParseError(ValueError):
    """Raised when a model response cannot be read as the expected object."""


def strip_code_fences(text: str) -> str:
    """Return the contents of the first fenced block, if there is one."""
    match = FENCE_RE.search(text)
    return match.group(1) if match else text


def isolate_json_object(text: str) -> Optional[dict]:
    """Find the first JSON object anywhere in the text.

    Scans every '{' and lets the decoder tell us where a well-formed object
    ends, so prose that happens to contain braces before the real payload
    does not derail us.
    """
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def parse_json_loose(raw: str, required_fields: Iterable[str] = ()) -> dict:
    """Parse a model response into a dict, or raise JSONParseError."""
    if raw is None:
        raise JSONParseError("empty response")

    text = str(raw).strip()
    if not text:
        raise JSONParseError("empty response")

    candidates = [strip_code_fences(text), text]
    data = None
    for candidate in candidates:
        data = isolate_json_object(candidate)
        if data is not None:
            break

    if data is None:
        raise JSONParseError("no JSON object found in response")

    missing = [field for field in required_fields if field not in data]
    if missing:
        raise JSONParseError(f"missing required field(s): {', '.join(missing)}")

    return data


async def generate_json(
    prompt: str,
    required_fields: Iterable[str] = (),
    *,
    system_prompt: Optional[str] = None,
    json_mode: bool = True,
    event: str = "llm_json",
) -> dict:
    """Ask the model for JSON, retrying once with a harder instruction.

    Raises LLMError if both attempts are unusable. There is deliberately no
    fallback value: a caller that cannot get an answer must surface that.
    """
    required = tuple(required_fields)

    raw = await llm_client.generate(prompt, system_prompt=system_prompt, json_mode=json_mode)
    try:
        return parse_json_loose(raw, required)
    except JSONParseError as first_error:
        logger.warning(f"{event}_retry", error=str(first_error))

    retry_prompt = f"{prompt}\n\n{RETRY_INSTRUCTION}"
    raw_retry = await llm_client.generate(
        retry_prompt, system_prompt=system_prompt, json_mode=json_mode
    )
    try:
        return parse_json_loose(raw_retry, required)
    except JSONParseError as second_error:
        logger.error(f"{event}_failed", error=str(second_error))
        raise LLMError("model did not return usable JSON") from second_error
