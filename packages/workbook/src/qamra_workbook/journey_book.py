"""«رحلتي الأولى للتعلّم» as printed books: the plan's pages with their print layer, and the audio items.

The plan (content/journey/plan.yaml) says what each page teaches. The print layer
(content/journey/stage-<n>.yaml) says how it prints: the vowelised title and instruction with {masc/fem}
variants, the engine page type when it differs from the plan's, the render params, and the audio item its
QR plays. Tareq reviewed the pages himself; the `# draft: educator review` marks in the layers and the catalog
are comments for whoever edits them next, and gate nothing.

Audio (Addendum 6 §4.8): a page with audio prints a QR to `https://{BRAND_DOMAIN}/a/{code}`, a short public
player with no child data. An item is a letter, a word or a page's sounds; its code comes from its key, so
a shared item (the letter ب) keeps one code on every page and in every order. `content/journey/audio.yaml`
is the catalog the API serves (staff upload the recordings item by item).

    uv run python -m qamra_workbook.journey_book check     # every stage's print layer against the plan
    uv run python -m qamra_workbook.journey_book audio     # rewrite content/journey/audio.yaml
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import functools
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from qamra_workbook.journey import Journey, JourneyPage, load
from qamra_workbook.names import clean_arabic, clean_latin_name
from qamra_workbook.render.spec import BookSpec, Child, Numerals, PageSpec, from_journey, product_geometry

# the repo's content/journey (QAMRA_CONTENT_DIR overrides content/, as for the story themes)
CONTENT = (
    Path(os.environ.get("QAMRA_CONTENT_DIR") or Path(__file__).resolve().parents[4] / "content") / "journey"
)
PLAN = CONTENT / "plan.yaml"
AUDIO = CONTENT / "audio.yaml"
TITLE_AR = "رحلتي الأولى للتعلّم"
STAGE_NAMES = {1: "المحطة الأولى", 2: "المحطة الثانية", 3: "المحطة الثالثة"}


# plan page types the journey draws with its own builder (sized for 3–6-year-olds and small letters)
JOURNEY_TYPES = {"letter-trace": "journey-letter-trace"}


def layer_path(stage: int) -> Path:
    return CONTENT / f"stage-{stage}.yaml"


def audio_code(key: str) -> str:
    """The item's short public code: 8 characters from its key (stable across orders and reprints)."""
    digest = hashlib.sha256(f"qamra-audio:{key}".encode()).digest()
    return base64.b32encode(digest).decode().lower()[:8]


class AudioSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str | None = None  # a shared item («letter:ar:ب»); default: the page («journey:s1:p28»)
    title: str | None = None  # the player's heading, for every child (no {child}); default: the page title
    say: str  # the script staff record, in order
    show: list[str] = Field(default_factory=list)  # the words or letters the player shows
    lang: Literal["ar", "en"] = "ar"
    tts: bool = False  # the TTS fallback may read `say` (words and letters, never sound effects)


class PrintPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    instruction: str | None = None
    type: str | None = None  # the engine page type, when it differs from the plan's
    params: dict[str, Any] = Field(default_factory=dict)  # render params (the plan's params stay the brief)
    audio: AudioSpec | None = None


class Cover(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front: dict[str, Any] = Field(default_factory=dict)
    back: dict[str, Any] = Field(default_factory=dict)


class PrintLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: int
    title_ar: str  # «المحطة الأولى: أستعدّ للرحلة»
    cover: Cover = Field(default_factory=Cover)
    pages: dict[int, PrintPage]


@dataclasses.dataclass(frozen=True)
class AudioItem:
    code: str
    key: str
    stage: int
    page: int
    title: str
    say: str
    show: tuple[str, ...]
    lang: str
    tts: bool

    def as_dict(self) -> dict[str, Any]:
        return {**dataclasses.asdict(self), "show": list(self.show)}


def load_layer(stage: int, root: Path = Path()) -> PrintLayer:
    return PrintLayer.model_validate(yaml.safe_load((root / layer_path(stage)).read_text(encoding="utf-8")))


def stage_of(plan: Journey, stage: int) -> list[JourneyPage]:
    return next(s.pages for s in plan.stages if s.stage == stage)


def audio_item(stage: int, page: JourneyPage, spec: AudioSpec, printed: str | None = None) -> AudioItem:
    """The page's audio item; the player's title is the printed title when it is the same for every child."""
    key = spec.key or f"journey:s{stage}:p{page.n}"
    title = spec.title or (printed if printed and "{" not in printed else page.title)
    return AudioItem(
        audio_code(key), key, stage, page.n, title, spec.say, tuple(spec.show), spec.lang, spec.tts
    )


def page_specs(plan: Journey, layer: PrintLayer) -> list[PageSpec]:
    """The stage's pages as engine pages: the plan page with its print layer over it."""
    out = []
    for page in stage_of(plan, layer.stage):
        spec = from_journey(page, layer.stage)
        printed = layer.pages.get(page.n, PrintPage())
        params = {**printed.params}
        if "lang" in params:
            params.pop("lang")
        instruction_en = str(params.pop("instruction_en", spec.instruction_en))
        if printed.audio is not None:
            params["audio_code"] = audio_item(layer.stage, page, printed.audio, printed.title).code
        params.setdefault("brief", dict(page.params))  # the plan's params, for builders that read them
        if (printed.type or JOURNEY_TYPES.get(page.type, page.type)) == "find-letter":
            params.setdefault("box_pitch", 18.0)  # three answer boxes stay inside a half-width card
        out.append(
            dataclasses.replace(
                spec,
                type=printed.type or JOURNEY_TYPES.get(page.type, page.type),
                title=printed.title or page.title,
                instruction=printed.instruction or page.instruction,
                lang=printed.params.get("lang", spec.lang),
                instruction_en=instruction_en,
                audio=printed.audio is not None,
                params=params,
            )
        )
    return out


def cover_specs(layer: PrintLayer) -> list[PageSpec]:
    """The front and back cover (card, no page numbers)."""
    return [
        PageSpec(
            id=f"journey-s{layer.stage}-cover-{side}",
            type=f"journey-cover-{side}",
            number=0,
            section="intro",
            title=TITLE_AR,
            instruction=layer.title_ar,
            stage=layer.stage,
            params={"stage": layer.stage, **getattr(layer.cover, side)},
        )
        for side in ("front", "back")
    ]


# draft: educator review — a plain transliteration, only the last resort for the English name pages: the
# parent gives the English spelling with the order (`name_en`), and an order printed with a guess is flagged
# on its book (`name_en_guessed`) for the reviewer. Consonants get an "a" between them so the name reads.
_LATIN = {
    "ا": "a",
    "أ": "a",
    "إ": "i",
    "آ": "a",
    "ب": "b",
    "ت": "t",
    "ث": "th",
    "ج": "j",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "th",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "z",
    "ع": "a",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "w",
    "ي": "y",
    "ة": "a",
    "ى": "a",
    "ء": "",
    "ؤ": "u",
    "ئ": "e",
}
_VOWELS = set("aeiou")


def latin_name(name: str) -> str:
    """«ليان» → «Lyan», «سلمى» → «Salma»: a readable Latin guess at the name, when the parent gave none."""
    words = clean_arabic(name).split()
    bare = words[0] if words else ""
    out = ""
    for k, ch in enumerate(bare):
        piece = _LATIN.get(ch, "")
        if ch == "ي" and 0 < k < len(bare) - 1 and bare[k + 1] not in "او":
            piece = "i"
        if ch == "و" and 0 < k < len(bare) - 1:
            piece = "ou" if k < len(bare) - 1 else "w"
        if out and piece and out[-1] not in _VOWELS and piece[0] not in _VOWELS:
            out += "a"
        out += piece
    return out[:1].upper() + out[1:] if out else "Name"


def english_name(child: Child, name_en: str = "") -> tuple[str, bool]:
    """The English spelling the pages print, and whether it is a guess: the parent's spelling (`name_en`,
    tidied by `names.clean_latin_name`) when it is one, else the child's name when it is already in English
    letters, else the transliteration of the Arabic name (the guess)."""
    given = clean_latin_name(name_en) or clean_latin_name(child.name)
    return (given, False) if given else (latin_name(child.name), True)


def uses_name_en(page: PageSpec) -> bool:
    """The page prints the child's English name: the English name-tracing page, or a text with {name_en}."""
    if page.type == "name-trace" and page.params.get("script") == "en":
        return True
    texts = [page.title, page.instruction, page.instruction_en]
    texts += [v for v in page.params.values() if isinstance(v, str)]
    return any("{name_en}" in t for t in texts)


def with_name_en(pages: list[PageSpec], child: Child, name_en: str = "") -> list[PageSpec]:
    """The English pages (the name-tracing page, the greetings «Well done, {name_en}!») get the child's Latin
    name: the parent's spelling (`name_en`), else the transliteration (`english_name`)."""
    latin = english_name(child, name_en)[0]
    return [
        dataclasses.replace(p, params={**p.params, "name_en": latin})
        if (p.lang == "en" or (p.type == "name-trace" and p.params.get("script") == "en"))
        and not p.params.get("name_en")
        else p
        for p in pages
    ]


@functools.cache
def stage_names(stage: int) -> tuple[bool, bool]:
    """(the stage prints the English name, the stage traces the Arabic name): stages 2 and 3 do both, stage 1
    neither. The order job flags a guessed English name or an untraceable Arabic name only where printed."""
    specs = page_specs(load(PLAN), load_layer(stage))
    traces_ar = any(p.type == "name-trace" and p.params.get("script", "ar") == "ar" for p in specs)
    return any(uses_name_en(p) for p in specs), traces_ar


def stage_book(
    pages: list[PageSpec],
    child: Child,
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
    name_en: str = "",
) -> BookSpec:
    return BookSpec(
        product="journey",
        title_ar=TITLE_AR,
        child=child,
        pages=tuple(with_name_en(pages, child, name_en)),
        date=day or dt.date.today(),
        numerals=numerals,
        audio_base=f"https://{domain.strip().rstrip('/')}/a/",
        geometry=product_geometry("journey"),
    )


def audio_items(plan: Journey, layer: PrintLayer) -> list[AudioItem]:
    """The stage's audio items, one per key (a shared item is listed on its first page)."""
    items: dict[str, AudioItem] = {}
    for page in stage_of(plan, layer.stage):
        printed = layer.pages.get(page.n, PrintPage())
        if printed.audio is not None:
            item = audio_item(layer.stage, page, printed.audio, printed.title)
            items.setdefault(item.key, item)
    return list(items.values())


# the find-letter page colours its letters red, blue, yellow, green in turn (workbook_find.CRAYONS)
_CRAYONS = ("احمر", "ازرق", "اصفر", "اخضر")
_MARKS = re.compile("[\u064b-\u0652\u0640]")


def colour_problems(spec: PageSpec) -> list[str]:
    """A find-letter instruction that names colours must name them in the page's order."""
    plain = _MARKS.sub("", spec.instruction).translate(str.maketrans("أإآ", "ااا"))
    named = [c for _, c in sorted((m.start(), m.group()) for c in _CRAYONS for m in re.finditer(c, plain))]
    return (
        []
        if named == list(_CRAYONS[: len(named)])
        else [f"p{spec.number}: colours must go {_CRAYONS}, not {named}"]
    )


def layer_problems(plan: Journey, layer: PrintLayer) -> list[str]:
    """What the engine can check before drawing: every page known to the plan and the engine, audio where the
    plan asks for it, one code per item, and player titles that fit every child."""
    import qamra_workbook.render.pages  # noqa: F401  (registers the page types)
    from qamra_workbook.render.registry import REGISTRY

    out = []
    numbers = {p.n for p in stage_of(plan, layer.stage)}
    out += [f"p{n}: not in the plan's stage {layer.stage}" for n in sorted(set(layer.pages) - numbers)]
    for spec in page_specs(plan, layer):
        if spec.type not in REGISTRY:
            out.append(f"p{spec.number}: page type {spec.type!r} is not in the engine")
        if spec.type == "find-letter":
            out += colour_problems(spec)
    for page in stage_of(plan, layer.stage):
        printed = layer.pages.get(page.n)
        if page.audio and (printed is None or printed.audio is None):
            out.append(f"p{page.n}: the plan gives it audio, the print layer has no audio item")
    codes: dict[str, str] = {}
    for item in audio_items(plan, layer):
        if codes.setdefault(item.code, item.key) != item.key:
            out.append(f"audio code {item.code} is shared by {codes[item.code]} and {item.key}")
        if "{" in item.title or "{" in item.say:
            out.append(f"p{item.page}: the player's texts are the same for every child (no placeholders)")
    return out


def catalog(plan: Journey, stages: list[int]) -> dict[str, Any]:
    """The audio catalog the API serves (content/journey/audio.yaml)."""
    items = [item.as_dict() for stage in stages for item in audio_items(plan, load_layer(stage))]
    return {"product": "journey", "items": items}


def built_stages(root: Path = Path()) -> list[int]:
    return sorted(int(p.stem.split("-")[1]) for p in (root / CONTENT).glob("stage-*.yaml"))


CATALOG_HEAD = (
    "# Generated by `uv run python -m qamra_workbook.journey_book audio` from content/journey/stage-*.yaml:\n"
    "# the audio items of «رحلتي الأولى للتعلّم». Edit the print layers, not this file.\n"
    "# draft: educator review (every `say` script and `show` word)\n"
)


def catalog_text(plan: Journey, stages: list[int]) -> str:
    body = yaml.safe_dump(catalog(plan, stages), allow_unicode=True, sort_keys=False, width=110)
    return CATALOG_HEAD + body


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    plan, stages = load(PLAN), built_stages()
    if args[:1] == ["audio"]:
        AUDIO.write_text(catalog_text(plan, stages), encoding="utf-8")
        print(f"{AUDIO}: {len(catalog(plan, stages)['items'])} audio items")
        return 0
    problems = [f"stage {s}: {line}" for s in stages for line in layer_problems(plan, load_layer(s))]
    if AUDIO.exists() and AUDIO.read_text(encoding="utf-8") != catalog_text(plan, stages):
        problems.append(f"{AUDIO} is out of date: run `python -m qamra_workbook.journey_book audio`")
    print("\n".join(f"✗ {p}" for p in problems) or f"stages {stages}: print layers match the plan")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
