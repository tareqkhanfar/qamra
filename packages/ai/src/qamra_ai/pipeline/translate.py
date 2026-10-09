"""«ترجمة»: an English draft of a theme's texts from its Arabic (Addendum 4 §3.5).

One call to the text model, made only when an editor asks for it after seeing the estimate. The English
keeps the placeholders ({name}, {companion}), writes gendered words as {boy/girl} variants, and matches the
story's pages one to one. An editor reviews the draft like any other theme version.
"""

import copy
import json
import math
from typing import Any

from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.cost import anthropic_estimate
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import NAME_SLOTS, Theme, max_words_for
from qamra_pdf.arabic_names import unmark

PROMPT_TOKENS = 700  # the rules above the texts
CHARS_PER_TOKEN_IN = 2.0  # Arabic (with its JSON): a conservative count
CHARS_PER_TOKEN_OUT = 3.0


class TranslatedPage(BaseModel):
    index: int
    text_en: str


class ThemeTranslation(BaseModel):
    title_en: str
    blurb_en: str = ""
    lesson_en: str = ""
    questions_en: list[str] = []
    pages: list[TranslatedPage]


def translation_source(theme: Theme) -> dict[str, Any]:
    """The Arabic texts the model sees (placeholders and {m/f} variants kept; an Arabic case mark,
    `{name:acc}`, is shown as `{name}`, since English names do not change)."""
    fp = theme.for_parents

    def plain(text: str) -> str:
        return unmark(text, NAME_SLOTS)

    return {
        "title_ar": plain(theme.title_ar),
        "blurb_ar": plain(theme.blurb_ar or ""),
        "lesson_ar": plain(fp.lesson_ar) if fp else "",
        "questions_ar": [plain(q) for q in fp.questions_ar] if fp else [],
        "pages": [{"index": p.index, "text_ar": plain(p.text_ar)} for p in theme.pages],
    }


def estimate(theme: Theme, model: str) -> tuple[int, int, float]:
    """(input tokens, output tokens, USD) for one translation: an upper-bound style estimate."""
    chars = len(json.dumps(translation_source(theme), ensure_ascii=False))
    tokens_in = PROMPT_TOKENS + math.ceil(chars / CHARS_PER_TOKEN_IN)
    tokens_out = 150 + math.ceil(chars / CHARS_PER_TOKEN_OUT)
    return tokens_in, tokens_out, round(anthropic_estimate(model, tokens_in, tokens_out), 4)


async def translate(rt: Runtime, theme: Theme, *, step: str) -> ThemeTranslation:
    system = prompts.render(
        "theme_translate",
        age_min=theme.age_range[0],
        age_max=theme.age_range[1],
        max_words=max_words_for(theme.age_range[0]),
    )
    source = json.dumps(translation_source(theme), ensure_ascii=False, indent=1)
    return await rt.ask(
        step=step, system=system, user=[source], schema=ThemeTranslation, kind="story", max_tokens=8000
    )


def apply_translation(definition: dict[str, Any], tr: ThemeTranslation) -> dict[str, Any]:
    """The definition with the English texts. The pages must line up one to one (else ValueError)."""
    out = copy.deepcopy(definition)
    pages: list[dict[str, Any]] = out.get("pages") or []
    english = {p.index: p.text_en.strip() for p in tr.pages}
    if (
        set(english) != {p.get("index") for p in pages}
        or len(english) != len(pages)
        or not all(english.values())
    ):
        raise ValueError("the translation's pages don't match the story's pages")
    for page in pages:
        page["text_en"] = english[page["index"]]
    if tr.title_en.strip():
        out["title_en"] = tr.title_en.strip()
    if tr.blurb_en.strip():
        out["blurb_en"] = tr.blurb_en.strip()
    fp = out.get("for_parents")
    if isinstance(fp, dict):
        if tr.lesson_en.strip():
            fp["lesson_en"] = tr.lesson_en.strip()
        if len(tr.questions_en) == len(fp.get("questions_ar") or []) and all(
            q.strip() for q in tr.questions_en
        ):
            fp["questions_en"] = [q.strip() for q in tr.questions_en]
    return out
