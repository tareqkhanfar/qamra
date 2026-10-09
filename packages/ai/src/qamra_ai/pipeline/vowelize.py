"""Classic texts, vowelized once (CLAUDE.md §3.4: full تشكيل for ages 3–7; Addendum 4 plan §2.13).

A Classic book's words are the theme's page templates. For Arabic they are vowelized once per gender by the
text model (an admin-side, one-time step, cached with the template and keyed by a hash of the source), with
`{name}` and `{companion}` kept as placeholders. Each book then fills in the name at no AI cost.

A name's case marks (`{name:acc}`, `{name:gen}`, `qamra_pdf.arabic_names`) are not part of the vowelized
source, so adding one never changes the hash or calls the model again: `fill` puts the template's marks back
slot by slot before it fills the name («وَضَمَّتْ أبا بكر», «إلى أبي بكر»), and «يا {name}» needs no mark.

A tashkeel fix in a theme text does change the source, so it ships with a matching fix of the cached
vowelized texts (`CORRECTIONS`, `corrected_cache`): the cache is patched and re-keyed in place on deploy
(`qamra seed-themes`), and no text is vowelized again.

The model may only add diacritics: every text is checked to be the same letters and placeholders as its
source once the diacritics are removed. A text that fails the check keeps its unvowelized source (and is
listed in `kept`), so a mistake can never change a word in a printed book.
"""

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.pipeline.models import Gender
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import NAME_SLOTS, Theme, render_template
from qamra_pdf.arabic_names import fill_names, remark

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_PLACEHOLDER = re.compile(r"\{(name|companion)\}")
KEEP = ("{name}", "{companion}")
DEDICATION_AR = "إلى {name:gen}، {نجمِنا الصغير/نجمتِنا الصغيرة}: {نحبُّكَ/نحبُّكِ} حتّى القمر."


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
    its case marks first, so `{name:acc}` and «يا {name}» print «أبا بكر», `{name:gen}` «أبي بكر»."""
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


# ---- tashkeel fixes that keep the cache -------------------------------------------------------------------

_MARKS = "[ً-ْٰ]"  # tanween, harakat, shadda, sukun, dagger alif
_LETTER = "ء-ي"


@dataclass(frozen=True)
class Correction:
    """A tashkeel fix in one theme's Arabic: `word` (its letters) takes `vowel` on its last letter when the
    next word starts with `next_word` (letters): «وَرَفَعَتْ الشَّهَادَةَ» → «وَرَفَعَتِ الشَّهَادَةَ» (a sukun
    before hamzat al-wasl takes a helping kasra). The same fix is made in the theme's definition (a `{m/f}`
    variant's closing brace may stand between the two words) and in a cached vowelization of it, whatever
    marks the model put on the word."""

    theme: str  # the theme's slug
    word: str
    next_word: str
    vowel: str = "ِ"  # kasra

    def pattern(self) -> re.Pattern[str]:
        letters = "".join(re.escape(c) + f"{_MARKS}*" for c in self.word[:-1]) + re.escape(self.word[-1])
        after = "".join(re.escape(c) + f"{_MARKS}*" for c in self.next_word)
        return re.compile(f"(?<![{_LETTER}])({letters}){_MARKS}*(\\}}?\\s+{after})")

    def apply(self, text: str) -> str:
        return self.pattern().sub(lambda m: m.group(1) + self.vowel + m.group(2), text)


# 2026-10-09: a sukun on a word-final consonant before «ال» (graduation p11, new-sibling p15; girls' texts)
CORRECTIONS: tuple[Correction, ...] = (
    Correction("graduation", "ورفعت", "الشهادة"),
    Correction("new-sibling", "وأرت", "الضيف"),
)


def _corrected(node: Any, fixes: Sequence[Correction]) -> Any:
    """Every string in `node` (a theme definition or cached texts) with `fixes` applied."""
    if isinstance(node, str):
        for fix in fixes:
            node = fix.apply(node)
        return node
    if isinstance(node, list):
        return [_corrected(v, fixes) for v in node]
    if isinstance(node, dict):
        return {k: _corrected(v, fixes) for k, v in node.items()}
    return node


def corrected_definition(definition: dict[str, Any]) -> dict[str, Any]:
    """A theme definition with the `CORRECTIONS` of its own theme applied (unchanged when none apply)."""
    fixes = [c for c in CORRECTIONS if c.theme == definition.get("slug")]
    return _corrected(definition, fixes) if fixes else definition


def corrected_cache(
    definition: dict[str, Any], cache: dict[str, Any], gender: Gender
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """A Classic template's pinned theme definition and its cached vowelization, both corrected and the cache
    re-keyed to the corrected source: (definition, cache), or None when there is nothing to correct. No model
    call: the same fix the theme file got, made in the cached words.

    A template with no cache, or a stale one (it waits for its new vowelization as before), gets the corrected
    definition only. A fresh cache is corrected only when the corrected texts still pass the words check;
    otherwise nothing is touched, so a fix never marks a wrong text as ready nor makes a ready one stale."""
    fixed = corrected_definition(definition)
    if fixed == definition:
        return None
    if not cache or cache.get("hash") != source_hash(sources(Theme.model_validate(definition), gender)):
        return fixed, cache
    fixes = [c for c in CORRECTIONS if c.theme == definition.get("slug")]
    texts = VowelizedTexts.model_validate(_corrected(cache["texts"], fixes))
    source = sources(Theme.model_validate(fixed), gender)
    pairs = [
        (source.title, texts.title),
        (source.dedication, texts.dedication),
        (source.lesson, texts.lesson),
        (source.blurb, texts.blurb),
        *zip(source.questions, texts.questions, strict=False),
        *zip((p.text for p in source.pages), (p.text for p in texts.pages), strict=False),
    ]
    if not all(same_words(src, new) for src, new in pairs):
        return None
    note = {"fixes": [f"{c.word} {c.next_word}" for c in fixes], "at": datetime.now(UTC).isoformat()}
    return fixed, {
        **cache,
        "hash": source_hash(source),
        "texts": texts.model_dump(),
        "corrected": [*cache.get("corrected", []), note],
    }
