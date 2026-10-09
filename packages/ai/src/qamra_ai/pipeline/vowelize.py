"""Classic texts, vowelized once (CLAUDE.md §3.4: full تشكيل for ages 3–7; Addendum 4 plan §2.13).

A Classic book's words are the theme's page templates. For Arabic they are vowelized once per gender by the
text model (an admin-side, one-time step, cached with the template and keyed by a hash of the source), with
`{name}` and `{companion}` kept as placeholders. Each book then fills in the name at no AI cost.

A name's case marks (`{name:acc}`, `qamra_pdf.arabic_names`) are not part of the vowelized source, so adding
one never changes the hash or calls the model again: `fill` puts the template's marks back slot by slot
before it fills the name («وَضَمَّتْ أبا بكر»), and «يا {name}» needs no mark («يا أبا بكر»).

The model may only add diacritics: every text is checked to be the same letters and placeholders as its
source once the diacritics are removed. A text that fails the check keeps its unvowelized source (and is
listed in `kept`), so a mistake can never change a word in a printed book.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field

from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.pipeline.models import Gender
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import NAME_SLOTS, Theme, render_template
from qamra_pdf.arabic_names import fill_names, remark

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_PLACEHOLDER = re.compile(r"\{(name|companion)\}")
KEEP = ("{name}", "{companion}")
DEDICATION_AR = "إلى {name}، {نجمِنا الصغير/نجمتِنا الصغيرة}: {نحبُّكَ/نحبُّكِ} حتّى القمر."


class VowelizedPage(BaseModel):
    index: int
    text: str


class VowelizedTexts(BaseModel):
    title: str
    dedication: str
    pages: list[VowelizedPage]
    lesson: str
    questions: list[str]
    blurb: str


def _resolve(template: str, gender: Gender) -> str:
    """The gender forms chosen, the placeholders kept: `{name}` stays `{name}`."""
    return render_template(template, gender, "{name}", "{companion}")


def sources(theme: Theme, gender: Gender) -> VowelizedTexts:
    """The Arabic texts of a Classic book for one gender, as written (placeholders kept)."""
    fp = theme.for_parents
    return VowelizedTexts(
        title=_resolve(theme.title_ar, gender),
        dedication=_resolve(DEDICATION_AR, gender),
        pages=[VowelizedPage(index=p.index, text=_resolve(p.text_ar, gender)) for p in theme.pages],
        lesson=_resolve(fp.lesson_ar, gender) if fp else "",
        questions=[_resolve(q, gender) for q in fp.questions_ar] if fp else [],
        blurb=_resolve(theme.blurb_ar or "", gender),
    )


def source_hash(texts: VowelizedTexts) -> str:
    """Changes whenever the theme's words change: a cached vowelization is only used for its own source."""
    raw = json.dumps(texts.model_dump(), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def plain(text: str) -> str:
    return _TASHKEEL.sub("", text)


def same_words(source: str, vowelized: str) -> bool:
    """Only diacritics were added: the same letters, spaces, punctuation and placeholders."""
    return plain(vowelized).split() == plain(source).split() and _PLACEHOLDER.findall(
        vowelized
    ) == _PLACEHOLDER.findall(source)


@dataclass
class Vowelized:
    texts: VowelizedTexts
    kept: list[str] = field(default_factory=list)  # texts that failed the check and stay unvowelized


def checked(source: VowelizedTexts, answer: VowelizedTexts) -> Vowelized:
    out = source.model_copy(deep=True)
    kept: list[str] = []

    def take(label: str, src: str, new: str) -> str:
        if same_words(src, new):
            return new
        kept.append(label)
        return src

    out.title = take("title", source.title, answer.title)
    out.dedication = take("dedication", source.dedication, answer.dedication)
    by_index = {p.index: p.text for p in answer.pages}
    for page in out.pages:
        page.text = take(f"page:{page.index}", page.text, by_index.get(page.index, ""))
    out.lesson = take("lesson", source.lesson, answer.lesson)
    if len(answer.questions) == len(source.questions):
        pairs = zip(source.questions, answer.questions, strict=True)
        out.questions = [take(f"question:{i}", q, a) for i, (q, a) in enumerate(pairs)]
    else:
        kept.append("questions")
    out.blurb = take("blurb", source.blurb, answer.blurb)
    return Vowelized(out, kept)


async def vowelize(rt: Runtime, theme: Theme, gender: Gender, *, step: str) -> Vowelized:
    """One call to the text model for one gender's texts; checked word by word."""
    source = sources(theme, gender)
    answer = await rt.ask(
        step=step,
        system=prompts.render("classic_vowelize", gender=gender),
        user=[json.dumps(source.model_dump(), ensure_ascii=False, indent=1)],
        schema=VowelizedTexts,
        kind="story",
        max_tokens=16000,
    )
    return checked(source, answer)


def fill(text: str, name: str, companion: str, template: str = "") -> str:
    """A cached text with the child's names: `template` (the theme text it was vowelized from) gives back
    its case marks first, so `{name:acc}` and «يا {name}» print «أبا بكر»."""
    if template:
        text = remark(text, template, NAME_SLOTS)
    return fill_names(text, {"name": name, "companion": companion})


TEXT_KEYS = ("title_ar", "title_en", "blurb_ar", "blurb_en", "for_parents")
PAGE_TEXT_KEYS = ("text_ar", "text_en", "beat")


def with_current_texts(pinned: dict[str, object], current: dict[str, object]) -> dict[str, object]:
    """The pinned theme (whose scenes the template's art shows) with the live theme's words, when its pages
    still line up one to one. Used when the team edits a theme's text after its template was drawn."""
    pinned_pages = pinned.get("pages")
    current_pages = current.get("pages")
    if not isinstance(pinned_pages, list) or not isinstance(current_pages, list):
        return pinned
    if [p.get("index") for p in pinned_pages] != [p.get("index") for p in current_pages]:
        return pinned  # the story itself changed: that needs a new template, not new words
    out = {**pinned, **{k: current[k] for k in TEXT_KEYS if k in current}}
    out["pages"] = [
        {**old, **{k: new[k] for k in PAGE_TEXT_KEYS if k in new}}
        for old, new in zip(pinned_pages, current_pages, strict=True)
    ]
    return out
