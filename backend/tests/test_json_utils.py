from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import LLMError
from app.services.json_utils import (
    JSONParseError,
    generate_json,
    isolate_json_object,
    parse_json_loose,
    strip_code_fences,
)


class TestParseJsonLoose:
    def test_plain_json(self):
        assert parse_json_loose('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        raw = '```json\n{"answer": "B"}\n```'
        assert parse_json_loose(raw, ["answer"]) == {"answer": "B"}

    def test_bare_fence_without_language(self):
        raw = "```\n{\"answer\": \"B\"}\n```"
        assert parse_json_loose(raw) == {"answer": "B"}

    def test_prose_wrapped_json(self):
        raw = 'Sure! Here is the JSON you asked for:\n{"answer": "B"}\nHope that helps.'
        assert parse_json_loose(raw, ["answer"])["answer"] == "B"

    def test_braces_appearing_before_the_object(self):
        raw = 'The {placeholder} is {"answer": "B"} and that is it.'
        assert parse_json_loose(raw, ["answer"]) == {"answer": "B"}

    def test_missing_required_field_raises(self):
        with pytest.raises(JSONParseError, match="suggested_answer"):
            parse_json_loose('{"options": []}', ["options", "suggested_answer"])

    def test_non_object_raises(self):
        with pytest.raises(JSONParseError):
            parse_json_loose('[1, 2, 3]')

    def test_empty_raises(self):
        with pytest.raises(JSONParseError):
            parse_json_loose("")

    def test_none_raises(self):
        with pytest.raises(JSONParseError):
            parse_json_loose(None)

    def test_garbage_raises(self):
        with pytest.raises(JSONParseError):
            parse_json_loose("I could not determine the answer.")

    def test_strip_code_fences_passthrough(self):
        assert strip_code_fences("no fence here") == "no fence here"

    def test_isolate_returns_none_without_object(self):
        assert isolate_json_object("nothing at all") is None


class TestGenerateJson:
    @pytest.mark.asyncio
    async def test_returns_parsed_object(self):
        with patch(
            "app.services.json_utils.llm_client.generate",
            new=AsyncMock(return_value='{"answer": "B"}'),
        ) as mock:
            result = await generate_json("q", ["answer"])

        assert result == {"answer": "B"}
        assert mock.await_count == 1
        assert mock.await_args.kwargs["json_mode"] is True

    @pytest.mark.asyncio
    async def test_retries_once_then_raises(self):
        with patch(
            "app.services.json_utils.llm_client.generate",
            new=AsyncMock(return_value="not json at all"),
        ) as mock:
            with pytest.raises(LLMError):
                await generate_json("q", ["answer"])

        assert mock.await_count == 2
        retry_prompt = mock.await_args.args[0]
        assert "Return ONLY valid JSON." in retry_prompt

    @pytest.mark.asyncio
    async def test_succeeds_on_the_retry(self):
        with patch(
            "app.services.json_utils.llm_client.generate",
            new=AsyncMock(side_effect=["garbage", '{"answer": "B"}']),
        ) as mock:
            result = await generate_json("q", ["answer"])

        assert result["answer"] == "B"
        assert mock.await_count == 2

    @pytest.mark.asyncio
    async def test_schema_invalid_twice_raises(self):
        with patch(
            "app.services.json_utils.llm_client.generate",
            new=AsyncMock(return_value='{"options": []}'),
        ) as mock:
            with pytest.raises(LLMError):
                await generate_json("q", ["options", "suggested_answer"])

        assert mock.await_count == 2

    @pytest.mark.asyncio
    async def test_fenced_answer_survives(self):
        fenced = '```json\n{"answer": "B"}\n```'
        with patch(
            "app.services.json_utils.llm_client.generate",
            new=AsyncMock(return_value=fenced),
        ):
            assert (await generate_json("q", ["answer"]))["answer"] == "B"
