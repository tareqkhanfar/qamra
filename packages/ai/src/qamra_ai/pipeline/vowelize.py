"""Classic texts, vowelized once (CLAUDE.md §3.4: full تشكيل for ages 3–7; Addendum 4 plan §2.13).

A Classic book's words are the theme's page templates. For Arabic they are vowelized once per gender by the
text model (an admin-side, one-time step, cached with the template and keyed by a hash of the source), with
`{name}` and `{companion}` kept as placeholders. Each book then fills in the name at no AI cost.

A name's case marks (`{name:acc}`, `{name:gen}`, `qamra_pdf.arabic_names`) are not part of the vowelized
source, so adding one never changes the hash or calls the model again: `fill` puts the template's marks back
slot by slot before it fills the name («وَضَمَّتْ أبا بكر», «إلى أبي بكر»), and «يا {name}» needs no mark.

A tashkeel or wording fix in a theme text does change the source, so it ships with a matching fix of the
cached vowelized texts (`CORRECTIONS`, `TEXT_FIXES`, `corrected_cache`): the cache is patched and re-keyed in
place on deploy (`qamra seed-themes`), and no text is vowelized again.

The model may only add diacritics: every text is checked to be the same letters and placeholders as its
source once the diacritics are removed, and to keep every gender-bearing last vowel the source wrote («مَعَكِ»
never turns into «مَعَكَ», `gender_marks_kept`). A text that fails the check keeps its unvowelized source (and
is listed in `kept`), so a mistake can never change a word or the hero's gender in a printed book.
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
from qamra_ai.pipeline.gender_check import final_mark, tokens
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


_GENDER_VOWELS = ("\u064e", "\u0650")  # fatha (to a boy), kasra (to a girl) on «ـكَ / ـكِ», «ـتَ / ـتِ», «أَنْتَ»


def gender_marks_kept(source: str, vowelized: str) -> bool:
    """No last vowel the source wrote on a word ending in «ك» or «ت» was swapped for the other gender's
    («مَعَكِ» → «مَعَكَ», «أَحْسَنْتَ» → «أَحْسَنْتِ»). The words are the same (`same_words`), so they pair up."""
    for a, b in zip(tokens(source), tokens(vowelized), strict=False):
        if not a.key.endswith(("ك", "ت")):
            continue
        was, now = final_mark(a.raw), final_mark(b.raw)
        if any(v in was for v in _GENDER_VOWELS) and any(v in now for v in _GENDER_VOWELS if v not in was):
            return False
    return True


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
        if same_words(src, new) and gender_marks_kept(src, new):
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
        system=prompts.render("classic_vowelize", version=2, gender=gender),
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


def _loose(words: str) -> str:
    """A regex for `words` (letters only) with any tashkeel after each letter and any spaces between words."""
    return r"\s+".join("".join(re.escape(c) + f"{_MARKS}*" for c in w) for w in words.split())


@dataclass(frozen=True)
class TextFix:
    """A wording fix in one theme's text (the gender review of 2026-10-09): `old` → `new`, both as written in
    the theme file (with their `{m/f}` braces). The theme's definition gets `new` for `old`. A Classic
    template's cached vowelization (Arabic, one gender) gets, for the old words rendered for that gender
    whatever marks the model gave them, the new words rendered for that gender as the file writes them: no
    model call, and the cache stays keyed to the words it holds (`corrected_cache`). An English fix only
    changes the definitions (the cache holds no English)."""

    theme: str
    old: str
    new: str

    def apply(self, text: str) -> str:
        return text.replace(self.old, self.new)

    def apply_cached(self, text: str, gender: Gender) -> str:
        old = plain(_resolve(self.old, gender))
        if not re.search("[\u0600-\u06ff]", old):
            return text
        new = _resolve(self.new, gender)
        pattern = re.compile(f"(?<![{_LETTER}]){_loose(old)}(?![{_LETTER}])")
        return pattern.sub(lambda _: new, text)


# 2026-10-09, the gender review: words that agree with the hero in every rendering (new-sibling «للأهل»:
# «تطمئنُه/تطمئنُها»), and the English that avoided a pronoun («hugged {him/her} tight»).
TEXT_FIXES: tuple[TextFix, ...] = (
    TextFix("new-sibling", "تطمئن الحكاية أنّ {مكانَه/مكانَها}", "{تُطَمْئِنُهُ/تُطَمْئِنُها} الحكاية بأنّ {مكانَه/مكانَها}"),
    TextFix(
        "new-sibling",
        "This story reassures that their place in the family's heart never changes, and invites them to be "
        "the proud big sibling.",
        "This story reassures {him/her} that {his/her} place in the family's heart never changes, and "
        "invites {him/her} to be the proud big {brother/sister}.",
    ),
    TextFix(
        "new-sibling",
        "The story of {name}, the proud big one,",
        "The story of {name}, the proud big {brother/sister},",
    ),
    TextFix("graduation", "got a green dot on its nose.", "got a green dot on his nose."),
    TextFix("graduation", "who hugged tight and said", "who hugged {him/her} tight and said"),
    TextFix(
        "first-day", 'together." And fell asleep smiling.', 'together." Then {he/she} fell asleep smiling.'
    ),
    TextFix("custom", "the people {name} loves.", "the people {he/she} loves."),
    TextFix(
        "custom", "{name} found the first thing {name} loves.", "{name} found the first thing {he/she} loves."
    ),
    TextFix(
        "custom", "{name} laughed with everyone {name} loves.", "{name} laughed with everyone {he/she} loves."
    ),
    TextFix(
        "custom",
        "{name} shared the happiness with the family.",
        "{name} shared {his/her} joy with {his/her} family.",
    ),
    # 2026-10-10: the catalog cards spoke of every hero as a boy («بطلنا»); they say «طفلك» to the parent, as
    # first-day and new-sibling do (a catalog text is read before the child is chosen: no {m/f} there)
    TextFix("olive-season", "يحمل بطلنا سلّته", "يحمل طفلك سلّته"),
    TextFix("neighborhood-friends", "يكتشف بطلنا أنّ الفرح", "يكتشف طفلك أنّ الفرح"),
    TextFix("neighborhood-friends", "معهم يكتشف بطلنا أن", "معهم يكتشف طفلك أن"),
    TextFix("moon-trip", "يأخذ بطلنا إلى", "يأخذ طفلك إلى"),
    TextFix("moon-trip", "يصنع بطلنا صاروخًا", "يصنع طفلك صاروخًا"),
)
FIXES: tuple[Correction | TextFix, ...] = (*CORRECTIONS, *TEXT_FIXES)


def _corrected(node: Any, fixes: Sequence[Correction | TextFix], gender: Gender | None = None) -> Any:
    """Every string in `node` with `fixes` applied: a theme definition (`gender` None), or the cached texts
    vowelized for one gender."""
    if isinstance(node, str):
        for fix in fixes:
            node = (
                fix.apply(node)
                if gender is None or isinstance(fix, Correction)
                else fix.apply_cached(node, gender)
            )
        return node
    if isinstance(node, list):
        return [_corrected(v, fixes, gender) for v in node]
    if isinstance(node, dict):
        return {k: _corrected(v, fixes, gender) for k, v in node.items()}
    return node


def corrected_definition(definition: dict[str, Any]) -> dict[str, Any]:
    """A theme definition with the `FIXES` of its own theme applied (unchanged when none apply)."""
    fixes = [c for c in FIXES if c.theme == definition.get("slug")]
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
    fixes = [c for c in FIXES if c.theme == definition.get("slug")]
    texts = VowelizedTexts.model_validate(_corrected(cache["texts"], fixes, gender))
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
    names = [f"{c.word} {c.next_word}" if isinstance(c, Correction) else c.new for c in fixes]
    note = {"fixes": names, "at": datetime.now(UTC).isoformat()}
    return fixed, {
        **cache,
        "hash": source_hash(source),
        "texts": texts.model_dump(),
        "corrected": [*cache.get("corrected", []), note],
    }
