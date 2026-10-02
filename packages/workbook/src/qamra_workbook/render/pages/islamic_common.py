"""What every page of «قلبي يعرف الله» shares: the page's content and context, the unit's ribbon, the framed
block that
prints a source's wording (or a marked placeholder), the drafter's short texts, and the registration of a
page type
with its `islamic-*` template.

A page prints religious wording only through the register: `sacred(...)` for a verse, a quotation or a dhikr
block, a
`Choice` that names a `source`, and the inline token `{src:ID}` inside a text. Each asks the resolver for a
source id and
gets the verified text, a candidate (preview builds only) or a placeholder. In a print build a placeholder,
or a source
that is not `scholar_approved`, is a problem: the page is never rendered.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from markupsafe import Markup, escape

from qamra_workbook.islamic_sources import NOTICE, Resolved, SourceError, Span
from qamra_workbook.pictures.islamic import ribbon_svg, scene_svg, star8_svg
from qamra_workbook.render.islamic_content import Choice, Claim, IslamicContext, Page, Quote
from qamra_workbook.render.islamic_units import UNITS
from qamra_workbook.render.registry import REGISTRY, Builder, Frame, PageContext, PageType

# the small tag of a block whose wording is not final (preview builds only; a print build refuses it)
PREVIEW_TAG = {
    "text_candidate": "نصّ مرشَّح — غير معتمد",
    "text_verified": "نسخ حرفي — بانتظار المشرف",
}
PREVIEW_SHORT = {"text_candidate": "مرشَّح", "text_verified": "بانتظار المشرف"}
TOKEN = re.compile(r"\{src:([a-z0-9-]+)\}")  # a source's wording inside a text: {src:d-eat-start}


@dataclass(frozen=True)
class IslamicPageType(PageType):
    """A page type whose template is `islamic-<name>.html.j2` (the series' pages share the `islamic-`
    prefix)."""

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


def page_of(ctx: PageContext) -> Page:
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
        "ribbon": ribbon_svg(motif, style.color, ink, g.page_w),
        "star": star8_svg("#C9962B", 7.4, "#FFFBEE"),
        "unit": ctx.text(style.name_ar),
        "ink": ink,
        "preview": context_of(ctx).mode == "preview",
        "marks": context_of(ctx).review_marks,
    }


def scene(ctx: PageContext, name: str, css_class: str = "scene", fit: str = "slice") -> Markup:
    """A scene of the series, with the cast (the reader and the recurring characters) when it has people."""
    return scene_svg(name, f"{ctx.page.id}-{css_class}", context_of(ctx).kit, css_class, fit)


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
    elif got.status != "scholar_approved":
        problems.append(
            f"{source_id}: {got.status}, not scholar_approved (a print build needs the scholar's approval)"
        )


def sacred(ctx: PageContext, quote: Quote, kind: str, problems: list[str]) -> dict[str, Any]:
    """The block for a verse, a quotation or a dhikr: the source's wording and where it comes from, or a
    marked
    placeholder. Never any wording of this module's own."""
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
    register
    (a candidate is underlined in a preview build; a placeholder shows its notice; a print build refuses
    both). The
    tokens are cut out before the text is personalized, so no digit of an id is turned into a numeral."""
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
        elif isl.mode == "preview" and got.status != "scholar_approved":
            parts.append(Markup('<span class="cand">{}</span>').format(got.text))
        else:
            parts.append(escape(got.text))
    return Markup("").join(parts)


def claim(ctx: PageContext, value: Claim | str, problems: list[str]) -> dict[str, Any]:
    """A short text: personalized (`{child}`, `{masc/fem}`, `{src:ID}`) and marked when the drafter wrote
    it.
    """
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
    """The citations under a page («21:87», «صحيح البخاري 6094»), in order of appearance and without
    repeats.
    """
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
