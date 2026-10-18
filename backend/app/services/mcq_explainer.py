import re
from typing import Optional

from app.core.exceptions import LLMError
from app.core.logging import logger
from app.services.json_utils import generate_json

# A./A)/(a)/1. style markers, allowing leading bullets, quotes or nav noise.
OPTION_MARKER_RE = re.compile(
    r"^[\s>*\u2022\-\u2013]*\(?([A-Za-z]|\d{1,2})[.)]\s*(\S.*?)\s*$"
)

# A line that reads like the start of a question: ends in '?' or opens with
# Q / Q1 / Question.
QUESTION_START_RE = re.compile(r"^\s*\(?(?:Q\d*|Question)\b", re.IGNORECASE)

MAX_REGION_CHARS = 4000
MAX_STEM_CHARS = 1200
MAX_OPTION_CHARS = 300
MAX_OPTIONS = 26
MAX_GAP_LINES = 8
# A numeric list is only trusted as an option list this soon after a question.
NUMERIC_QUESTION_WINDOW = 3
# How much of the page after a question line to hand the model.
REGION_WINDOW_LINES = 40


def label_for(index: int) -> str:
    return chr(ord("A") + index)


def normalize_options(options) -> list[dict]:
    """Accept ['text', ...] or [{'label', 'text'}, ...] -> canonical list.

    Text is authoritative from whoever supplied it (the page, typically);
    labels are positional A, B, C... so the model and the UI agree on
    identifiers regardless of how the page numbered things.
    """
    out: list[dict] = []
    for option in options or []:
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


def _marker_kind(marker: str) -> tuple[Optional[str], Optional[int]]:
    """Classify a marker as ('letter', rank) or ('numeric', rank)."""
    value = marker.strip()
    if len(value) == 1 and value.isalpha():
        return "letter", ord(value.upper()) - ord("A") + 1
    if value.isdigit() and 0 < int(value) <= 99:
        return "numeric", int(value)
    return None, None


def _is_question_like(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    return bool(QUESTION_START_RE.match(stripped))


def _collect_hits(lines: list[str]) -> list[dict]:
    hits = []
    for index, line in enumerate(lines):
        match = OPTION_MARKER_RE.match(line)
        if not match:
            continue
        kind, rank = _marker_kind(match.group(1))
        text = match.group(2).strip()
        if kind is None or not text:
            continue
        hits.append({"line": index, "rank": rank, "kind": kind, "text": text})
    return hits


def _runs(hits: list[dict], kind: str) -> list[list[dict]]:
    """Every run of >=2 consecutive ranks of one marker kind."""
    filtered = [hit for hit in hits if hit["kind"] == kind]
    runs = []
    for index, start in enumerate(filtered):
        sequence = [start]
        for candidate in filtered[index + 1:]:
            previous = sequence[-1]
            consecutive = candidate["rank"] == previous["rank"] + 1
            close_enough = candidate["line"] - previous["line"] <= MAX_GAP_LINES
            if consecutive and close_enough:
                sequence.append(candidate)
        if len(sequence) >= 2:
            runs.append(sequence)
    return runs


def _numeric_eligible(run: list[dict], question_lines: list[int]) -> bool:
    """A numeric list only counts as options when a question sits just above it.

    Numbered lists are everywhere in page chrome; requiring a question line
    within a few lines of the first number keeps nav out of the options.
    """
    start = run[0]["line"]
    return any(0 <= start - q <= NUMERIC_QUESTION_WINDOW for q in question_lines)


def _select_run(runs: list[list[dict]], last_question_line: Optional[int]) -> list[dict]:
    if not runs:
        return []

    def score(run: list[dict]):
        start = run[0]["line"]
        if last_question_line is not None and start > last_question_line:
            # Nearest run after the last question wins.
            return (0, start - last_question_line, -len(run))
        return (1, 0, -len(run))

    return min(runs, key=score)


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


def _locate_run(lines: list[str]) -> tuple[list[dict], list[str]]:
    """Best option run over the whole text, as (hits, option texts).

    Lettered markers always win: if any letter run exists we never look at
    numbered lists, and a numbered list is only considered when a question
    line sits within a few lines above it.
    """
    hits = _collect_hits(lines)
    if not hits:
        return [], []

    question_lines = [i for i, line in enumerate(lines) if _is_question_like(line)]
    last_question_line = question_lines[-1] if question_lines else None

    run = _select_run(_runs(hits, "letter"), last_question_line)
    if not run:
        numeric = [r for r in _runs(hits, "numeric") if _numeric_eligible(r, question_lines)]
        run = _select_run(numeric, last_question_line)

    if len(run) < 2:
        return [], []
    return run, [hit["text"][:MAX_OPTION_CHARS] for hit in run]


def find_option_run(page_text: str) -> tuple[list[dict], str]:
    """Pull an option list out of raw page text without asking the model.

    Scans the whole text, so a question far down a long page is still found.
    Returns (options, stem); empty options when nothing looked like a choice
    list.
    """
    lines = (page_text or "").splitlines()
    if not lines:
        return [], ""

    run, texts = _locate_run(lines)
    if len(run) < 2:
        return [], ""

    options = [
        {"label": label_for(i), "text": text}
        for i, text in enumerate(texts[:MAX_OPTIONS])
    ]
    return options, _stem_before(lines, run[0]["line"])


def bounded_region(page_text: str, max_chars: int = MAX_REGION_CHARS) -> str:
    """The stem+options region, or a window after the last question line.

    Never returns the head of the page: the interesting text is wherever the
    question is, which on a long lesson page may be tens of thousands of
    characters in. Returns "" when the page shows no question signal at all.
    """
    lines = (page_text or "").splitlines()
    if not lines:
        return ""

    run, texts = _locate_run(lines)
    if run:
        stem = _stem_before(lines, run[0]["line"])
        listed = "\n".join(f"{label_for(i)}. {text}" for i, text in enumerate(texts))
        return f"{stem}\n{listed}".strip()[:max_chars]

    question_lines = [i for i, line in enumerate(lines) if _is_question_like(line)]
    if not question_lines:
        return ""
    start = question_lines[-1]
    return "\n".join(lines[start:start + REGION_WINDOW_LINES]).strip()[:max_chars]


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
        found by regex anywhere in the page text, then a bounded model call
        over the stem+options region. Raises LLMError rather than guessing.
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

        region = bounded_region(page_text or "")
        if not region:
            # A DOM-captured stem is still a usable bounded region.
            region = (question_text or "").strip()[:MAX_REGION_CHARS]
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
