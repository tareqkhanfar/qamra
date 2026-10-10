"""What every page of «قلبي يعرف الله» shares: the page's content and context, the unit's ribbon, the framed
block that prints a source's wording (or a marked placeholder), the drafter's short texts, and the
registration of a page type with its `islamic-*` template.

A page prints religious wording only through the register: `sacred(...)` for a verse, a quotation or a dhikr
block, a `Choice` that names a `source`, and the inline token `{src:ID}` inside a text. Each asks the resolver
for a source id and gets the verified text, a candidate (preview builds only) or a placeholder. In a print
build a placeholder, or a source that is not `scholar_approved`, is a problem: the page is never rendered."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from markupsafe import Markup, escape

from qamra_workbook.islamic_sources import APPROVED, NOTICE, Resolved, SourceError, Span
from qamra_workbook.pictures.islamic import SCENES, ribbon_svg, scene_svg, star8_svg
from qamra_workbook.pictures.islamic_backdrops import composed_problems, composed_svg, prop_known, prop_svg
from qamra_workbook.render.islamic_content import AnyPage, Choice, Claim, IslamicContext, Quote, Scene
from qamra_workbook.render.islamic_figures import CAST
from qamra_workbook.render.islamic_units import UNITS
from qamra_workbook.render.registry import REGISTRY, Builder, Frame, PageContext, PageType

# the small tag of a block whose wording is not final (preview builds only; a print build refuses it)
PREVIEW_TAG = {
    "text_candidate": "نصّ مرشَّح — غير معتمد",
    "text_verified": "نسخ حرفي — بانتظار المشرف",
}
PREVIEW_SHORT = {"text_candidate": "مرشَّح", "text_verified": "بانتظار المشرف"}
TOKEN = re.compile(r"\{src:([a-z0-9-]+)\}")  # a source's wording inside a text: {src:d-eat-start}
RIBBON_H = 12.0  # mm of the unit's ribbon below the trim (islamic-book.css: .isl-ribbon adds the bleed)


@dataclass(frozen=True)
class IslamicPageType(PageType):
    """A page type whose template is `islamic-<name>.html.j2` (the series' `islamic-` prefix)."""

    shared: str = ""  # a page type that shares another's template (`prayer-steps` uses the wudu cards)

    @property
    def template(self) -> str:
        stem = self.shared or self.name
        stem = stem if stem.startswith("islamic-") else f"islamic-{stem}"
        return f"pages/{stem}.html.j2"


def islamic_page(name: str, *, frame: Frame = "sheet", shared: str = "") -> Callable[[Builder], Builder]:
    """Register a builder as the page type `name` (its template is `islamic-<name>.html.j2`, or the `shared`
    one)."""

    def register(build: Builder) -> Builder:
        if name in REGISTRY:
            raise ValueError(f"page type {name!r} is registered twice")
        REGISTRY[name] = IslamicPageType(name, build, frame, shared)
        return build

    return register


def context_of(ctx: PageContext) -> IslamicContext:
    isl = ctx.page.params["islamic"]
    assert isinstance(isl, IslamicContext)
    return isl


def page_of(ctx: PageContext) -> AnyPage:
    return ctx.page.params["page"]  # type: ignore[no-any-return]


def chrome(ctx: PageContext, problems: list[str]) -> dict[str, Any]:
    """The unit's identity on a page: the ribbon with its motif, the chip, and the preview legend."""
    page = page_of(ctx)
    style = ctx.style
    unit = UNITS.get(page.unit)
    g = ctx.book.geometry
    ink = unit.on_color if unit else "#FFFFFF"
    motif = unit.motif if unit else "stars"
    for text in (ctx.page.title, ctx.page.instruction):
        if "{src:" in text:
            problems.append(f"a title or an instruction cannot hold a {{src:…}} token: {text!r}")
    return {
        "ribbon": ribbon_svg(motif, style.color, ink, g.page_w, RIBBON_H, g.bleed),
        "star": star8_svg("#C9962B", 7.4, "#FFFBEE"),
        "unit": ctx.text(style.name_ar),
        "ink": ink,
        "preview": context_of(ctx).mode == "preview",
        "marks": context_of(ctx).review_marks,
    }


def scene(
    ctx: PageContext, name: str | Scene, css_class: str = "scene", fit: str = "slice", n: int = 0
) -> Markup:
    """A scene of the series, drawn (`art`) or composed (`backdrop` + `props` + `figures`), with the cast (the
    reader and the recurring characters) when it has people. Check it first with `scene_problems`. `n` tells
    apart two scenes of one page (their gradients' ids)."""
    uid = f"{ctx.page.id}-{css_class}" + (f"-{n}" if n else "")
    kit = context_of(ctx).kit
    if isinstance(name, str):
        return scene_svg(name, uid, kit, css_class, fit)
    if name.art:
        return scene_svg(name.art, uid, kit, css_class, fit)
    return composed_svg(name.backdrop, name.props, name.figures, uid, kit, css_class, fit)


def scene_problems(value: Scene, *, people: bool = True, where: str = "scene") -> list[str]:
    """What stops a scene from being drawn: an unknown art or backdrop, a prop that is not in the library or
    draws a person, and (`people=False`, a prophet's or a sira story) any person at all."""
    if value.art:
        art = SCENES.get(value.art)
        if art is None:
            return [f"{where}: no scene art {value.art!r}"]
        if not people and (art.figures or value.figures):
            return [f"{where}: {value.art!r} draws people, and this page shows none"]
        return []
    return [
        f"{where}: {p}" for p in composed_problems(value.backdrop, value.props, value.figures, people=people)
    ]


def picture_problems(names: list[str], where: str) -> list[str]:
    """Pictures a page names (library ids or isl:<icon>) that do not exist or draw a person."""
    from qamra_workbook.pictures.islamic_backdrops import PERSON_PICTURES

    out = []
    for name in names:
        if not prop_known(name):
            out.append(f"{where}: no picture {name!r} in the library (or isl:<icon>)")
        elif name in PERSON_PICTURES:
            out.append(f"{where}: {name!r} draws a person; people appear only as the recurring characters")
    return out


def picture(name: str, size: float = 100.0, css_class: str = "pic", i: int = 0) -> Markup:
    """A library picture or a series icon as its own SVG (checked with `picture_problems` first)."""
    return Markup(  # nosec B704 (static art)
        f'<svg class="{css_class}" viewBox="0 0 {size:g} {size:g}" aria-hidden="true">'
        f"{prop_svg(name, 0, 0, size, i)}</svg>"
    )


SPEAKERS = frozenset({*CAST, "reader", "naanaa"})


# ---- the register's wording on a page -------------------------------------------------------------------


def _resolve(ctx: PageContext, source_id: str, span: Span | None = None) -> tuple[Resolved | None, str]:
    """(what the register gives, why there is no text): a failing marker is a reason, never a guess."""
    try:
        got = context_of(ctx).resolver.resolve(source_id, span)
    except SourceError as err:
        return None, str(err)
    return got, got.placeholder


def _print_gate(
    ctx: PageContext, source_id: str, got: Resolved | None, reason: str, problems: list[str]
) -> None:
    """In a print build, a placeholder or an unapproved source stops the page."""
    if context_of(ctx).mode != "print":
        return
    if got is None or got.text is None:
        problems.append(f"{source_id}: a placeholder in a print build ({reason})")
    elif got.status not in APPROVED:
        problems.append(f"{source_id}: {got.status}, not approved (a print build needs an approved source)")


def sacred(ctx: PageContext, quote: Quote, kind: str, problems: list[str]) -> dict[str, Any]:
    """The block for a verse, a quotation or a dhikr: the source's wording and where it comes from, or a
    marked placeholder. Never any wording of this module's own."""
    isl = context_of(ctx)
    span = Span(quote.span.start, quote.span.end) if quote.span else None
    got, reason = _resolve(ctx, quote.source, span)
    src = isl.resolver.register.by_id.get(quote.source)
    text = got.text if got else None
    _print_gate(ctx, quote.source, got, reason, problems)
    status = got.status if got else "proposed"
    preview = isl.mode == "preview" and text is not None
    return {
        "kind": kind,
        "id": quote.source,
        "label": ctx.text(quote.label) if quote.label else "",
        "title": src.title_ar if src else quote.source,
        "text": text,
        "lines": [
            {"n": ctx.num(n) if n else "", "text": t}
            for n, t in (got.lines if got and got.kind == "quran" else ())
        ],
        "reference": ctx.num(got.reference) if got and got.reference else "",
        "quran": bool(got and got.kind == "quran"),
        "placeholder": text is None,
        "notice": got.notice
        if got and got.notice
        else NOTICE.get(src.kind if src else "quran", NOTICE["quran"]),
        "reason": reason,
        "tag": PREVIEW_TAG.get(status, "") if preview else "",
        "short_tag": PREVIEW_SHORT.get(status, "") if preview else "",
    }


def rich(ctx: PageContext, text: str, problems: list[str]) -> str | Markup:
    """A text as printed for this child, with each `{src:ID}` replaced by that source's wording from the
    register (a candidate is underlined in a preview build; a placeholder shows its notice; a print build
    refuses both). The tokens are cut out before the text is personalized, so no digit of an id is turned into
    a numeral."""
    if "{src:" not in text:
        return ctx.text(text)
    isl = context_of(ctx)
    parts: list[str | Markup] = []
    for i, piece in enumerate(TOKEN.split(text)):
        if i % 2 == 0:
            parts.append(escape(ctx.text(piece)))
            continue
        got, reason = _resolve(ctx, piece)
        _print_gate(ctx, piece, got, reason, problems)
        if got is None or got.text is None:
            notice = got.notice if got and got.notice else NOTICE["dua"]
            parts.append(Markup('<span class="hole">{}</span>').format(notice))
        elif isl.mode == "preview" and got.status not in APPROVED:
            parts.append(Markup('<span class="cand">{}</span>').format(got.text))
        else:
            parts.append(escape(got.text))
    return Markup("").join(parts)


def plain(ctx: PageContext, text: str) -> str:
    """A text as printed for this child, in plain words for the answer key: each `{src:ID}` replaced by that
    source's wording (the page itself, built with `rich`, gates and marks it), personalized like `rich`."""
    if "{src:" not in text:
        return ctx.text(text)
    parts = []
    for i, piece in enumerate(TOKEN.split(text)):
        if i % 2 == 0:
            parts.append(ctx.text(piece))
            continue
        got, _ = _resolve(ctx, piece)
        parts.append(got.text if got is not None and got.text else "…")
    return "".join(parts)


def answer_lines(ctx: PageContext, question: str, choices: list[dict[str, Any]]) -> list[str]:
    """The answer key of a question: the question itself, then its right answer (a bare «الجواب: اللهُ»
    under the page's title could read as the answer to the title)."""
    right = "، ".join(str(c["text"]) for c in choices if c["ok"])
    return [plain(ctx, question), f"الجواب: {right}"]


def claim(ctx: PageContext, value: Claim | str, problems: list[str]) -> dict[str, Any]:
    """A short text: personalized (`{child}`, `{masc/fem}`, `{src:ID}`) marked when drafted."""
    if isinstance(value, str):
        return {"text": rich(ctx, value, problems), "ai": False, "sources": []}
    return {"text": rich(ctx, value.text, problems), "ai": value.ai_drafted, "sources": value.sources}


def choice(ctx: PageContext, option: Choice, problems: list[str]) -> dict[str, Any]:
    """An answer to tick: typed text, or the wording of the source it names."""
    base: dict[str, Any] = {
        "ok": option.ok,
        "feedback": ctx.text(option.feedback),
        "placeholder": False,
        "tag": "",
        "notice": "",
    }
    if not option.source:
        return {**base, "text": rich(ctx, option.t, problems)}
    block = sacred(ctx, Quote(source=option.source, span=option.span), "choice", problems)
    return {
        **base,
        "text": block["text"] or "",
        "placeholder": block["placeholder"],
        "notice": block["notice"],
        "tag": block["short_tag"],
    }


def references(ctx: PageContext, ids: list[str]) -> list[str]:
    """The citations under a page («21:87», «صحيح البخاري 6094»), in order, without repeats."""
    isl = context_of(ctx)
    out: dict[str, None] = {}
    for source_id in ids:
        if source_id not in isl.resolver.register.by_id:
            continue
        got, _ = _resolve(ctx, source_id)
        if got is not None and got.reference:
            out[ctx.num(got.reference)] = None
    return list(out)


def tokens_in(text: str) -> list[str]:
    """The source ids a text pulls in with `{src:ID}`."""
    return TOKEN.findall(text)


def source_ids(value: Claim | Choice | str) -> list[str]:
    """Every source id a text, a claim or a choice stands on: its `sources`, its `source`, its `{src:ID}`
    tokens."""
    if isinstance(value, str):
        return tokens_in(value)
    if isinstance(value, Claim):
        return [*value.sources, *tokens_in(value.text)]
    return [value.source] if value.source else tokens_in(value.t)
