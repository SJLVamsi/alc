import json
from unittest.mock import patch

import pytest

from app.services.note_generator import NoteGenerator
from app.services.flashcard_generator import FlashcardService


@pytest.mark.asyncio
async def test_note_generator_fallback():
    gen = NoteGenerator()
    result = gen._fallback_notes("Test Lesson", "Short content")
    assert "summary" in result
    assert result["summary"] is not None


def test_flashcard_intervals():
    service = FlashcardService()
    assert service.calculate_next_review(5) == 60
    assert service.calculate_next_review(0) == 1
    assert service.calculate_next_review(3) == 14


def test_flashcard_intervals_default():
    service = FlashcardService()
    assert service.calculate_next_review(3, current_interval=1) == 14


class TestCodingAssistant:
    def test_fallback_explanation(self):
        from app.services.coding_assistant import CodingAssistant
        ca = CodingAssistant()
        result = ca._fallback_explanation("Test problem")
        assert "explanation" in result
        assert "algorithms" in result
        assert "data_structures" in result

    def test_fallback_review(self):
        from app.services.coding_assistant import CodingAssistant
        ca = CodingAssistant()
        result = ca._fallback_review()
        assert "feedback" in result
        assert result["time_complexity"] == "O(n)"


class TestMCQExplainer:
    @pytest.mark.asyncio
    async def test_supplied_options_skip_extraction(self):
        from app.services.mcq_explainer import MCQExplainer

        mcq = MCQExplainer()
        with patch(
            "app.services.mcq_explainer.generate_json",
            side_effect=AssertionError("should not call the model"),
        ):
            result = await mcq.extract_question(
                page_text="ignored",
                question_text="Which is FIFO?",
                options=["Stack", "Queue"],
            )

        assert result["source"] == "supplied"
        assert [o["label"] for o in result["options"]] == ["A", "B"]
        assert [o["text"] for o in result["options"]] == ["Stack", "Queue"]

    @pytest.mark.asyncio
    async def test_regex_extracts_options_from_messy_page(self):
        from app.services.mcq_explainer import MCQExplainer

        page = "\n".join([
            "NxtWave  Courses  Practice  Contests",
            "1. Home",
            "2. Profile",
            "Which data structure follows FIFO ordering?",
            "A) Stack",
            "B) Queue",
            "C) Binary tree",
            "D) Hash map",
            "Submit",
        ])
        mcq = MCQExplainer()
        result = await mcq.extract_question(page_text=page)

        assert result["source"] == "regex"
        assert [o["text"] for o in result["options"]] == [
            "Stack", "Queue", "Binary tree", "Hash map",
        ]
        assert "FIFO" in result["question_text"]
        # nav entries must not become options
        assert "Home" not in " ".join(o["text"] for o in result["options"])

    def test_regex_handles_lowercase_and_numeric_markers(self):
        from app.services.mcq_explainer import find_option_run

        options, _ = find_option_run("Pick one\n(a) alpha\n(b) beta\n(c) gamma")
        assert [o["text"] for o in options] == ["alpha", "beta", "gamma"]

        # a numeric list is only trusted directly under a question
        options, _ = find_option_run("Which one is first?\n1. one\n2. two\n3. three")
        assert [o["text"] for o in options] == ["one", "two", "three"]

    def test_numbered_nav_does_not_beat_lettered_options(self):
        from app.services.mcq_explainer import find_option_run

        page = "\n".join([
            "Course home",
            "1. Introduction",
            "2. Setup",
            "3. Variables",
            "Which keyword declares a constant?",
            "A) let",
            "B) const",
        ])
        options, _ = find_option_run(page)
        assert [o["text"] for o in options] == ["let", "const"]

    def test_letter_run_wins_even_when_numeric_run_is_longer(self):
        from app.services.mcq_explainer import find_option_run

        page = "\n".join([
            "Which one is correct?",
            "1. a", "2. b", "3. c", "4. d", "5. e",
            "Now pick from these",
            "A) yes",
            "B) no",
        ])
        options, _ = find_option_run(page)
        assert [o["text"] for o in options] == ["yes", "no"]

    def test_numeric_list_without_a_question_is_ignored(self):
        from app.services.mcq_explainer import find_option_run

        options, _ = find_option_run("Shopping list\n1. milk\n2. bread\n3. eggs")
        assert options == []

    def test_picks_letter_run_closest_after_the_last_question(self):
        from app.services.mcq_explainer import find_option_run

        page = "\n".join([
            "Q1) First question?",
            "A) alpha",
            "B) beta",
            "Q2) Second question?",
            "A) gamma",
            "B) delta",
        ])
        options, _ = find_option_run(page)
        assert [o["text"] for o in options] == ["gamma", "delta"]

    def test_finds_mcq_far_down_a_long_page(self):
        from app.services.mcq_explainer import find_option_run

        filler = "\n".join(f"filler line {i} with a few ordinary words" for i in range(700))
        assert len(filler) > 20000
        page = filler + "\nWhich structure is FIFO?\nA. Stack\nB. Queue\n"

        options, stem = find_option_run(page)
        assert [o["text"] for o in options] == ["Stack", "Queue"]
        assert "FIFO" in stem
        assert page.index("FIFO") > 20000

    @pytest.mark.asyncio
    async def test_no_mcq_at_all_raises(self):
        from app.core.exceptions import LLMError
        from app.services.mcq_explainer import MCQExplainer

        mcq = MCQExplainer()
        with patch(
            "app.services.mcq_explainer.generate_json",
            side_effect=AssertionError("must not ask the model without a question"),
        ):
            with pytest.raises(LLMError):
                await mcq.extract_question(page_text="Just prose about trees.")

    @pytest.mark.asyncio
    async def test_model_fallback_gets_the_region_not_the_page_head(self):
        from app.services.mcq_explainer import MCQExplainer

        filler = "\n".join(f"filler {i} words words words" for i in range(400))
        page = filler + "\nWhich structure is FIFO?\nThe first one in is first out."

        captured = {}

        async def fake_generate_json(prompt, required_fields=(), **kwargs):
            captured["prompt"] = prompt
            return {
                "question_text": "Which structure is FIFO?",
                "options": [{"label": "A", "text": "Stack"}, {"label": "B", "text": "Queue"}],
            }

        mcq = MCQExplainer()
        with patch("app.services.mcq_explainer.generate_json", new=fake_generate_json):
            result = await mcq.extract_question(page_text=page)

        assert result["source"] == "model"
        assert "FIFO" in captured["prompt"]
        assert "filler 0 words" not in captured["prompt"]
        assert len(captured["prompt"]) < 4500

    @pytest.mark.asyncio
    async def test_never_defaults_to_option_a_when_model_fails(self):
        from app.core.exceptions import LLMError
        from app.services.mcq_explainer import MCQExplainer

        mcq = MCQExplainer()
        with patch(
            "app.services.mcq_explainer.generate_json",
            side_effect=LLMError("model did not return usable JSON"),
        ):
            with pytest.raises(LLMError):
                await mcq.explain_question("Q?", ["one", "two"])

    @pytest.mark.asyncio
    async def test_fenced_json_answer_b_stays_b(self):
        from app.services.mcq_explainer import MCQExplainer

        mcq = MCQExplainer()
        with patch(
            "app.services.mcq_explainer.generate_json",
            return_value={
                "options": [
                    {"label": "A", "explanation": "Stack is LIFO."},
                    {"label": "B", "explanation": "Queue is FIFO."},
                ],
                "suggested_answer": "B",
                "overall_reasoning": "FIFO means first in, first out.",
            },
        ):
            result = await mcq.explain_question("FIFO?", ["Stack", "Queue"])

        assert result["suggested_answer"] == "B"
        assert [o["is_correct"] for o in result["options"]] == [False, True]
        assert result["options"][1]["text"] == "Queue"

    @pytest.mark.asyncio
    async def test_answer_outside_option_set_is_rejected(self):
        from app.core.exceptions import LLMError
        from app.services.mcq_explainer import MCQExplainer

        mcq = MCQExplainer()
        with patch(
            "app.services.mcq_explainer.generate_json",
            return_value={
                "options": [],
                "suggested_answer": "E",
                "overall_reasoning": "made up",
            },
        ):
            with pytest.raises(LLMError, match="not one of the options"):
                await mcq.explain_question("FIFO?", ["Stack", "Queue"])

    @pytest.mark.asyncio
    async def test_option_text_comes_from_the_page_not_the_model(self):
        from app.services.mcq_explainer import MCQExplainer

        mcq = MCQExplainer()
        with patch(
            "app.services.mcq_explainer.generate_json",
            return_value={
                "options": [
                    {"label": "A", "text": "INVENTED", "explanation": "e1"},
                    {"label": "B", "text": "ALSO INVENTED", "explanation": "e2"},
                ],
                "suggested_answer": "B",
                "overall_reasoning": "r",
            },
        ):
            result = await mcq.explain_question("Q", ["Real A", "Real B"])

        assert [o["text"] for o in result["options"]] == ["Real A", "Real B"]


class TestKnowledgeBase:
    def test_dashboard_stats_empty(self, db_session):
        from app.services.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        stats = kb.get_dashboard_stats(db_session)
        assert stats.lessons_completed == 0
        assert stats.total_lessons > 0
        assert stats.study_time_minutes == 0.0


class _FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeAsyncClient:
    """Captures the payload and replays canned NDJSON lines / chat replies."""

    def __init__(self, lines=None, reply="fake reply"):
        self._lines = lines or []
        self._reply = reply
        self.payload = None
        self.url = None
        self.method = None

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, json=None):
        self.method, self.url, self.payload = method, url, json
        return _FakeStreamResponse(self._lines)

    async def post(self, url, json=None):
        self.method, self.url, self.payload = "POST", url, json
        return _FakePostResponse(self._reply)


class _FakePostResponse:
    def __init__(self, reply):
        self._reply = reply

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._reply}}


class TestLLMClientStreaming:
    @pytest.mark.asyncio
    async def test_chat_stream_yields_deltas(self):
        from app.services.llm_client import LLMClient

        lines = [
            json.dumps({"message": {"content": "Hel"}, "done": False}),
            "",
            json.dumps({"message": {"content": "lo"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]
        fake = _FakeAsyncClient(lines)

        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            chunks = [
                c async for c in client.chat_stream([{"role": "user", "content": "hi"}])
            ]

        assert chunks == ["Hel", "lo"]

    @pytest.mark.asyncio
    async def test_chat_stream_sets_num_ctx(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient([json.dumps({"message": {"content": "x"}, "done": True})])

        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            [c async for c in client.chat_stream([{"role": "user", "content": "hi"}])]

        assert fake.payload["stream"] is True
        assert fake.payload["options"]["num_ctx"] >= 8192

    @pytest.mark.asyncio
    async def test_chat_stream_ignores_malformed_lines(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(["not json", json.dumps({"message": {"content": "ok"}, "done": True})])

        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            chunks = [c async for c in client.chat_stream([{"role": "user", "content": "hi"}])]

        assert chunks == ["ok"]


class TestLLMClientGenerate:
    @pytest.mark.asyncio
    async def test_generate_goes_through_chat_endpoint(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="the answer")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            out = await client.generate("What is a BST?")

        assert out == "the answer"
        assert fake.url.endswith("/api/chat")
        assert fake.payload["messages"] == [{"role": "user", "content": "What is a BST?"}]
        # callers' API is unchanged: one prompt in, text out

    @pytest.mark.asyncio
    async def test_generate_system_prompt_becomes_a_system_message(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="x")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q", system_prompt="be terse")

        assert fake.payload["messages"][0] == {"role": "system", "content": "be terse"}
        assert fake.payload["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_json_mode_sets_format(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply='{"a": 1}')
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q", json_mode=True)

        assert fake.payload["format"] == "json"

    @pytest.mark.asyncio
    async def test_json_mode_is_off_by_default(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="plain")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q")

        assert "format" not in fake.payload

    @pytest.mark.asyncio
    async def test_options_carry_num_ctx_and_temperature(self):
        from app.services.llm_client import LLMClient

        fake = _FakeAsyncClient(reply="x")
        with patch("app.services.llm_client.httpx.AsyncClient", fake):
            client = LLMClient()
            await client.generate("q")

        options = fake.payload["options"]
        assert options["num_ctx"] >= 8192
        assert options["temperature"] == 0.2
