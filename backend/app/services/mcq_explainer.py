import re
from typing import Optional

from app.core.exceptions import LLMError
from app.core.logging import logger
from app.services.json_utils import generate_json

# A./A)/(a)/1. style markers, allowing leading bullets, quotes or nav noise.
OPTION_MARKER_RE = re.compile(
    r"^[\s>*\u2022\-\u2013]*\(?([A-Za-z]|\d{1,2})[.)]\s*(\S.*?)\s*$"
)

MAX_REGION_CHARS = 4000
MAX_STEM_CHARS = 1200
MAX_OPTION_CHARS = 300
MAX_OPTIONS = 26
MAX_GAP_LINES = 8


def label_for(index: int) -> str:
    return chr(ord("A") + index)


def normalize_options(options) -> list[dict]:
    """Accept ['text', ...] or [{'label', 'text'}, ...] -> canonical list.

    Text is authoritative from whoever supplied it (the page, typically);
    labels are positional A, B, C... so the model and the UI agree on
    identifiers regardless of how the page numbered things.
    """
    out: list[dict] = []
    for index, option in enumerate(options or []):
        if isinstance(option, dict):
            text = str(option.get("text", "")).strip()
        else:
            text = str(option).strip()
        if not text:
            continue
        out.append({"label": label_for(len(out)), "text": text[:MAX_OPTION_CHARS]})
        if len(out) >= MAX_OPTIONS:
            break
    return out


def _marker_rank(marker: str) -> Optional[int]:
    value = marker.strip().upper()
    if len(value) == 1 and value.isalpha():
        return ord(value) - ord("A") + 1
    if value.isdigit() and int(value) > 0:
        return int(value)
    return None


def _best_run(hits: list[dict]) -> list[dict]:
    """Longest run of consecutive markers (A,B,C / 1,2,3) with no big gaps."""
    runs = []
    for index, start in enumerate(hits):
        sequence = [start]
        for candidate in hits[index + 1:]:
            previous = sequence[-1]
            consecutive = candidate["rank"] == previous["rank"] + 1
            close_enough = candidate["line"] - previous["line"] <= MAX_GAP_LINES
            if consecutive and close_enough:
                sequence.append(candidate)
        runs.append(sequence)

    if not runs:
        return []
    # Longest wins; prefer a run starting at A/1; then the later one.
    runs.sort(key=lambda run: (len(run), run[0]["rank"] == 1, run[0]["line"]))
    return runs[-1]


def _stem_before(lines: list[str], first_option_line: int) -> str:
    collected: list[str] = []
    total = 0
    for line in reversed(lines[:first_option_line]):
        stripped = line.strip()
        if not stripped:
            continue
        collected.insert(0, stripped)
        total += len(stripped)
        if total >= MAX_STEM_CHARS:
            break
    return "\n".join(collected)[-MAX_STEM_CHARS:]


def find_option_run(page_text: str) -> tuple[list[dict], str]:
    """Pull an option list out of raw page text without asking the model.

    Returns (options, stem). Empty options when nothing looked like a choice
    list. Only the region around the markers is ever used, never the whole
    page.
    """
    if not page_text:
        return [], ""

    lines = page_text.splitlines()
    hits = []
    for index, line in enumerate(lines):
        match = OPTION_MARKER_RE.match(line)
        if not match:
            continue
        rank = _marker_rank(match.group(1))
        text = match.group(2).strip()
        if rank is None or not text:
            continue
        hits.append({"line": index, "rank": rank, "text": text})

    run = _best_run(hits)
    if len(run) < 2:
        return [], ""

    options = [
        {"label": label_for(i), "text": hit["text"][:MAX_OPTION_CHARS]}
        for i, hit in enumerate(run[:MAX_OPTIONS])
    ]
    return options, _stem_before(lines, run[0]["line"])


def _extraction_prompt(region: str) -> str:
    return f"""Extract the multiple choice question from this page region.

Region:
{region}

Return ONLY valid JSON with:
- question_text: the question stem
- options: list of {{"label": "A", "text": "..."}} in the order shown
"""


def _explanation_prompt(question_text: str, options: list[dict]) -> str:
    options_text = "\n".join(f"{o['label']}. {o['text']}" for o in options)
    labels = ", ".join(o["label"] for o in options)
    return f"""Analyze this multiple choice question.

Question:
{question_text}

Options:
{options_text}

For every option give a brief reasoning line explaining why it is correct
or incorrect. Work out the reasoning BEFORE stating the final answer.

Return ONLY valid JSON with:
- options: list of {{"label": "A", "explanation": "..."}} covering every
  option above
- suggested_answer: the label of the single correct option, one of: {labels}
- overall_reasoning: one or two sentences summarising the decision
"""


class MCQExplainer:
    async def extract_question(
        self,
        page_text: str = "",
        question_text: str = "",
        options=None,
    ) -> dict:
        """Resolve {question_text, options} from whatever the caller has.

        Order of preference: options the caller already scraped, then options
        found by regex in the page text, then a bounded model call over the
        captured stem. Raises LLMError rather than guessing.
        """
        supplied = normalize_options(options)
        if len(supplied) >= 2:
            stem = (question_text or "").strip()[:MAX_STEM_CHARS] or "Question"
            return {"question_text": stem, "options": supplied, "source": "supplied"}

        regex_options, stem = find_option_run(page_text or "")
        if len(regex_options) >= 2:
            return {
                "question_text": (question_text or stem).strip()[:MAX_STEM_CHARS],
                "options": regex_options,
                "source": "regex",
            }

        # Nothing looked like an option list. Ask the model, but only about the
        # bounded stem we captured - not the first N chars of the whole page.
        region = (question_text or page_text or "").strip()[:MAX_REGION_CHARS]
        if not region:
            raise LLMError("no multiple choice question found on the page")

        logger.info("mcq_extraction_fallback", region_chars=len(region))
        data = await generate_json(
            _extraction_prompt(region),
            required_fields=("question_text", "options"),
            event="mcq_extraction",
        )
        model_options = normalize_options(data.get("options"))
        if len(model_options) < 2:
            raise LLMError("model could not extract the answer options")

        return {
            "question_text": str(data.get("question_text") or region).strip()[:MAX_STEM_CHARS],
            "options": model_options,
            "source": "model",
        }

    async def explain_question(self, question_text: str, options) -> dict:
        """Explain each option and name the answer, validating against the page.

        The option text and the set of valid labels come from the caller, never
        from the model, so the model cannot introduce an option that was not on
        the page or answer with something outside the list.
        """
        canonical = normalize_options(options)
        if len(canonical) < 2:
            raise LLMError("fewer than two options to explain")

        labels = [option["label"] for option in canonical]
        data = await generate_json(
            _explanation_prompt(question_text, canonical),
            required_fields=("options", "suggested_answer", "overall_reasoning"),
            event="mcq_explanation",
        )
        return self._validate_explanation(canonical, labels, data)

    def _validate_explanation(self, canonical: list[dict], labels: list[str], data: dict) -> dict:
        answer = str(data.get("suggested_answer", "")).strip().upper()
        if answer not in labels:
            logger.error("mcq_answer_out_of_range", answer=answer, labels=labels)
            raise LLMError("model returned an answer that is not one of the options")

        reasoning: dict[str, str] = {}
        for item in data.get("options") or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip().upper()
            if label in labels and label not in reasoning:
                reasoning[label] = str(item.get("explanation", "")).strip()

        return {
            "options": [
                {
                    "label": option["label"],
                    "text": option["text"],
                    "is_correct": option["label"] == answer,
                    "explanation": reasoning.get(option["label"]) or "(no reasoning given)",
                }
                for option in canonical
            ],
            "suggested_answer": answer,
            "overall_reasoning": str(data.get("overall_reasoning", "")).strip(),
        }


mcq_explainer = MCQExplainer()
