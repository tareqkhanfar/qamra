"""The build checks of «قلبي يعرف الله» (Addendum 10 §3, §7, §10), over pages given as plain dicts (the sample
pages of content/islamic/samples.yaml, later the volumes' pages) and the source register.

Every check returns a list of `Problem`; an `error` fails the build. What they enforce:

* every religious block (a verse, a quotation, a dhikr, a dua, and the statements of a page's sourced
    fields) has at least one source id, and every id exists and is of the right kind;
* a page that gets coloured, cut, stuck or thrown away (`sacred: false` in plan.yaml, or `sacred_text: none`)
    carries no source, verse, quotation or dhikr at all (§3.6);
* the no-depiction rule (§3.5): a page tagged `prophet_story` or `angels` (a prophet's or a sira story is
    tagged by its type) declares no person in its scene region (the narrator panel may show the recurring
    characters), its scene art draws none, and no picture on it is a person, a body part or the reader;
    on every page, a library picture of a person is never a prop (people appear only as the cast);
* a print build fails while any placeholder or any unapproved source (`APPROVED`) is used (`check_print`);
* religious wording is never typed: a text that contains a register dhikr or verse (matched on the letters
only) must
    use `{src:ID}`, and a quiz option that is wording names a `source` (`typed-wording`; on a page that must
    carry no
    sacred text at all it is a `sacred-page` problem); plain non-religious options stay typed;
* the scholar's open decisions are collected for the review queue (`scholar_queue`)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from qamra_workbook.islamic_sources import (
    APPROVED,
    PLAN,
    TEXT_KINDS,
    Resolver,
    SourceError,
    Span,
    at_least,
    letters,
)

Level = Literal["error", "warning"]


@dataclass(frozen=True)
class Problem:
    code: str
    where: str  # a page id or a source id
    message: str
    level: Level = "error"

    def __str__(self) -> str:
        mark = "✗" if self.level == "error" else "!"
        return f"{mark} [{self.code}] {self.where}: {self.message}"


def errors(problems: Iterable[Problem]) -> list[Problem]:
    return [p for p in problems if p.level == "error"]


# ---- what a page's dict may carry -----------------------------------------------------------------------

PRINTS_WORDING = ("verse", "quote", "dhikr")  # blocks that print a source's wording: each needs `source`
REFERENCE_KEYS = ("source", "sources", "dua", "scholar_points", *PRINTS_WORDING)
# which source kinds each wording block may draw on
ALLOWED_KINDS: dict[str, frozenset[str]] = {
    "verse": frozenset({"quran"}),
    "quote": frozenset({"hadith", "quran", "dua"}),
    "dhikr": frozenset({"dua", "quran"}),
    "dua": frozenset({"dua"}),
    "choice": frozenset({"dua", "quran"}),  # a quiz option that is wording
    "inline": frozenset({"dua", "quran"}),  # {src:ID} inside a text
}
TOKEN = re.compile(r"\{src:([a-z0-9-]+)\}")
# a quiz option or a side of a match whose `source` prints that source's wording
WORDING_OPTION = re.compile(r"(^|\.)(choices\[\d+\]|pairs\[\d+\]\.[ab])$")
# keys whose strings are not prose: ids, art names, and the search markers of a span (never printed)
NOT_PROSE = frozenset(
    {
        "id",
        "key",
        "pic",
        "pics",
        "backdrop",
        "props",
        "who",
        "runner",
        "goal",
        "collect",
        "others",
        "hints",
        "picture",
        "icon",
        "layout",
        "size",
        "planned",
        "type",
        "unit",
        "volume",
        "engine_type",
        "art",
        "source",
        "sources",
        "dua",
        "from",
        "lang",
        "tags",
        "flags",
        "figures",
        "scholar_points",
        "start",
        "end",
        "sacred_text",
        "photo_slot",
        "stamps_from",
        "kind",
        "frame",
    }
)
# Fields whose text is a religious statement on that page type: each element needs a `source`/`sources`. The
# drafter's framing (`intro`, `explain`) states no ruling and is not on these lists.
SOURCED_FIELDS: dict[str, tuple[str, ...]] = {
    "prophet-story": ("scenes", "lesson", "question"),
    "order-steps": ("steps",),
    "prayer-steps": ("steps",),
    "dhikr": ("dhikr", "why", "manner"),
    "wwyd": ("quote", "sources"),
    "wdif": ("quote", "meaning"),
    "blessings-hunt": ("closing",),
    "unit-review": ("true_false", "choose"),
    "parent-guide": ("learned", "habit"),
    "surah": ("verse", "meaning"),
    "sira-story": ("scenes", "lesson", "question"),
    "pillar-card": ("idea",),
    "true-false": ("statements",),
    "choose": ("questions",),
    "self-test": ("true_false", "questions"),
    "quiz": ("true_false", "questions"),
    "assessment": ("true_false", "questions", "situations"),
}
DEPICTION_TAGS = frozenset({"prophet_story", "angels"})
# a page of this type is tagged even if the file forgot
IMPLIED_TAGS = {"prophet-story": "prophet_story", "sira-story": "prophet_story"}
# the keys that name a picture (a library id, `isl:<icon>`, a scene, or `reader` for the maze's runner)
PICTURE_KEYS = ("pic", "pics", "props", "others", "goal", "runner", "collect", "hints", "art", "picture")
SCENE_KEYS = ("scenes", "scene")  # the scene region of a page
FIGURE_KEYS = ("figures", "figure", "people", "person", "characters")
NARRATORS = frozenset({"huda", "reem", "salem", "reader", "naanaa"})  # the recurring characters only


@dataclass(frozen=True)
class PageRules:
    """What plan.yaml says about each page type: may it carry sacred text?"""

    sacred: Mapping[str, bool]

    @classmethod
    def load(cls, path: Path = PLAN) -> PageRules:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls({k: bool(v.get("sacred", True)) for k, v in raw.get("page_types", {}).items()})

    def may_carry_sacred(self, page: Mapping[str, Any]) -> bool:
        if page.get("sacred_text") == "none":
            return False
        ptype = str(page.get("type", ""))
        if ptype not in self.sacred:  # a content type that fills a plan type (front-title fills front)
            from qamra_workbook.render.islamic_content import plan_type

            ptype = plan_type(ptype)
        return self.sacred.get(ptype, True)


@dataclass(frozen=True)
class Ref:
    path: str
    key: str  # source | sources | dua | scholar_points
    ids: tuple[str, ...]


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Every dict inside `node`, with its path."""
    if isinstance(node, Mapping):
        yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}[{i}]")


def _strings(node: Any, path: str = "", key: str = "") -> Iterator[tuple[str, str, str]]:
    """Every string of the page with its path and the key it sits under."""
    if isinstance(node, str):
        yield path, key, node
    elif isinstance(node, Mapping):
        for k, value in node.items():
            yield from _strings(value, f"{path}.{k}" if path else str(k), str(k))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, f"{path}[{i}]", key)


def refs(page: Mapping[str, Any]) -> list[Ref]:
    """Every source id the page mentions, and where: `source`, `sources`, `dua`, `scholar_points` and the
    `{src:ID}` tokens inside its texts."""
    out: list[Ref] = []
    for path, node in _walk(page):
        for key in ("source", "sources", "dua", "scholar_points"):
            value = node.get(key)
            if isinstance(value, str) and key in ("source", "dua"):
                out.append(Ref(f"{path}.{key}" if path else key, key, (value,)))
            elif isinstance(value, list) and key in ("sources", "scholar_points"):
                out.append(Ref(f"{path}.{key}" if path else key, key, tuple(str(v) for v in value)))
    for path, key, text in _strings(page):
        found = TOKEN.findall(text)
        if found and key not in NOT_PROSE:
            out.append(Ref(path, "inline", tuple(found)))
    return out


def page_ids(page: Mapping[str, Any]) -> list[str]:
    """The distinct source ids a page uses, in order of appearance."""
    seen: dict[str, None] = {}
    for ref in refs(page):
        seen.update(dict.fromkeys(ref.ids))
    return list(seen)


@dataclass(frozen=True)
class WordingRequest:
    """A block that prints a source's wording (a verse, a quotation, a dhikr, a dua) as the page asks."""

    path: str
    block: str  # verse | quote | dhikr | dua
    source: str
    span: Span | None = None


def wording_requests(page: Mapping[str, Any]) -> list[WordingRequest]:
    out: list[WordingRequest] = []
    for path, node in _walk(page):
        for block in PRINTS_WORDING:
            value = node.get(block)
            if isinstance(value, Mapping) and isinstance(value.get("source"), str):
                span = Span.of(value["span"]) if isinstance(value.get("span"), Mapping) else None
                out.append(WordingRequest(f"{path}.{block}" if path else block, block, value["source"], span))
        if isinstance(node.get("dua"), str):
            out.append(WordingRequest(f"{path}.dua" if path else "dua", "dua", node["dua"]))
        if WORDING_OPTION.search(path) and isinstance(node.get("source"), str):
            span = Span.of(node["span"]) if isinstance(node.get("span"), Mapping) else None
            out.append(WordingRequest(path, "choice", node["source"], span))
    for path, key, text in _strings(page):
        if key not in NOT_PROSE:
            out += [WordingRequest(path, "inline", source_id) for source_id in TOKEN.findall(text)]
    return out


# ---- the page checks ------------------------------------------------------------------------------------


def _has_source(node: Any) -> bool:
    if not isinstance(node, Mapping):
        return False
    return bool(node.get("sources")) or isinstance(node.get("source"), str)


def _fields(page: Mapping[str, Any], name: str) -> list[tuple[str, Any]]:
    value = page.get(name)
    if value is None:
        return []
    if isinstance(value, list):
        return [(f"{name}[{i}]", v) for i, v in enumerate(value)]
    return [(name, value)]


def check_page(page: Mapping[str, Any], resolver: Resolver, rules: PageRules) -> list[Problem]:
    """The source-id, sacred-page and no-depiction checks of one page."""
    pid = str(page.get("id", "?"))
    ptype = str(page.get("type", ""))
    out: list[Problem] = []
    known = resolver.register.by_id

    for ref in refs(page):  # every id exists
        for source_id in ref.ids:
            if source_id not in known:
                out.append(
                    Problem("unknown-source", pid, f"{ref.path}: no source {source_id!r} in the register")
                )
    for req in wording_requests(page):  # the wording blocks name a source of the right kind
        src = known.get(req.source)
        if src is not None and src.kind not in ALLOWED_KINDS[req.block]:
            out.append(
                Problem(
                    "wrong-kind",
                    pid,
                    f"{req.path}: {req.source} is a {src.kind}, not usable as a {req.block}",
                )
            )
    for path, node in _walk(page):  # a wording block without a source id
        for block in PRINTS_WORDING:
            if block in node and not (
                isinstance(node[block], Mapping) and isinstance(node[block].get("source"), str)
            ):
                out.append(Problem("no-source", pid, f"{path + '.' if path else ''}{block} has no source id"))
        if "sources" in node and not node["sources"]:
            out.append(Problem("no-source", pid, f"{path + '.' if path else ''}sources is empty"))
        if "dua" in node and not isinstance(node["dua"], str):
            out.append(Problem("no-source", pid, f"{path + '.' if path else ''}dua has no source id"))
    for name in SOURCED_FIELDS.get(ptype, ()):  # the page type's religious statements are all sourced
        for path, value in _fields(page, name):
            if name in PRINTS_WORDING:
                continue  # checked above
            if not _has_source(value) and not (name == "sources" and value):
                out.append(Problem("no-source", pid, f"{path} is a religious statement without a source id"))

    for path, node in _walk(page):  # a quiz option is typed text or a source, never neither or both
        if re.search(r"(^|\.)choices\[\d+\]$", path) and bool(node.get("t")) == isinstance(
            node.get("source"), str
        ):
            out.append(
                Problem(
                    "bad-choice",
                    pid,
                    f"{path} needs either typed text `t` or a `source`, not both and not neither",
                )
            )
    sacred_type = rules.may_carry_sacred(page)
    for path, key, text in _strings(
        page
    ):  # religious wording is never typed (a plain non-religious option stays typed)
        if key in NOT_PROSE or not any("؀" <= ch <= "ۿ" for ch in text):
            continue
        folded = letters(TOKEN.sub("", text))
        hit = next((sid for sid, wording in resolver.wordings() if wording in folded), None)
        if hit is not None:
            code = "typed-wording" if sacred_type else "sacred-page"
            out.append(
                Problem(
                    code,
                    pid,
                    f"{path}: the wording of {hit} is typed in the text: "
                    f"use {{src:{hit}}} (in a choice, `source: {hit}`)",
                )
            )

    if not rules.may_carry_sacred(page):  # coloured, cut or thrown-away pages
        for ref in refs(page):
            out.append(
                Problem(
                    "sacred-page", pid, f"a page that gets coloured/cut/stuck carries a source: {ref.path}"
                )
            )
        for path, node in _walk(page):
            for block in PRINTS_WORDING:
                if block in node:
                    out.append(
                        Problem(
                            "sacred-page",
                            pid,
                            f"a page that gets coloured/cut/stuck carries a {block}: {path}",
                        )
                    )

    out += _depiction(page, pid)
    return out


def _pictures(page: Mapping[str, Any]) -> Iterator[tuple[str, str]]:
    """(path, picture name) of every picture the page names."""
    for path, node in _walk(page):
        for key in PICTURE_KEYS:
            value = node.get(key)
            where = f"{path}.{key}" if path else key
            if isinstance(value, str) and value:
                yield where, value
            elif isinstance(value, list):
                yield from ((f"{where}[{i}]", v) for i, v in enumerate(value) if isinstance(v, str))


def _depiction(page: Mapping[str, Any], pid: str) -> list[Problem]:
    from qamra_workbook.pictures.islamic import SCENES  # (the art says which scenes draw people)
    from qamra_workbook.pictures.islamic_backdrops import BACKDROPS, BODY_PICTURES, PERSON_PICTURES

    out: list[Problem] = []
    for path, name in _pictures(page):  # on every page: people are only the cast, never a library picture
        if name in PERSON_PICTURES:
            out.append(
                Problem("depiction", pid, f"{path}: {name!r} draws a person; people appear only as the cast")
            )
    tags = set(page.get("tags") or ()) | {
        IMPLIED_TAGS[t] for t in [str(page.get("type", ""))] if t in IMPLIED_TAGS
    }
    if not tags & DEPICTION_TAGS:
        return out
    shown = "/".join(sorted(tags & DEPICTION_TAGS))
    for path, name in _pictures(page):
        scene = SCENES.get(name)
        if name in BODY_PICTURES or name == "reader" or name in NARRATORS or (scene and scene.figures):
            out.append(Problem("depiction", pid, f"{path}: {name!r} shows a person on a {shown} page"))
    for name in SCENE_KEYS:
        for path, scene in _fields(page, name):
            if not isinstance(scene, Mapping):
                continue
            for key in FIGURE_KEYS:
                if scene.get(key):
                    out.append(
                        Problem(
                            "depiction",
                            pid,
                            f"{path} declares a person ({key}) on a "
                            f"{'/'.join(sorted(tags & DEPICTION_TAGS))} page",
                        )
                    )
            art = scene.get("art")
            backdrop = scene.get("backdrop")
            if art and art not in SCENES:
                out.append(Problem("unknown-art", pid, f"{path}: no scene art {art!r}"))
            elif art and SCENES[art].figures:
                out.append(Problem("depiction", pid, f"{path}: the scene art {art!r} draws people"))
            if backdrop and backdrop not in BACKDROPS:
                out.append(Problem("unknown-art", pid, f"{path}: no backdrop {backdrop!r}"))
    narrator = page.get("narrator")
    if isinstance(narrator, Mapping):
        for who in narrator.get("figures") or ():
            if who not in NARRATORS:
                out.append(
                    Problem(
                        "depiction", pid, f"narrator figure {who!r} is not one of the recurring characters"
                    )
                )
    return out


def load_pages(path: Path) -> list[dict[str, Any]]:
    """The pages of a samples file (a top-level `pages:` list of dicts)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [dict(p) for p in raw.get("pages", [])]


def check_pages(pages: Iterable[Mapping[str, Any]], resolver: Resolver, rules: PageRules) -> list[Problem]:
    return [p for page in pages for p in check_page(page, resolver, rules)]


# ---- the register ---------------------------------------------------------------------------------------


def check_register(resolver: Resolver) -> list[Problem]:
    """Problems of the register itself: a dua's hadith, markers that do not match, rulings' bases, approvals
    that lack a reviewer, a status above the wording that exists."""
    reg = resolver.register
    out: list[Problem] = []
    for src in reg.sources:
        if src.kind == "dua" and src.dua is not None:
            parent = reg.by_id.get(src.dua.from_)
            if parent is None:
                out.append(Problem("bad-dua", src.id, f"dua.from {src.dua.from_!r} does not exist"))
                continue
            if parent.kind != "hadith":
                out.append(
                    Problem("bad-dua", src.id, f"dua.from {parent.id!r} is a {parent.kind}, not a hadith")
                )
                continue
        for basis in src.basis:
            if basis not in reg.by_id:
                out.append(Problem("unknown-source", src.id, f"basis {basis!r} does not exist"))
        try:
            got = resolver.resolve(src.id)
        except SourceError as err:
            out.append(Problem("marker" if src.kind == "dua" else "register", src.id, str(err)))
            continue
        if src.kind in TEXT_KINDS and got.text is None and at_least(src.status, "text_verified"):
            out.append(Problem("no-text", src.id, f"status {src.status} but no wording ({got.placeholder})"))
        if src.decided and (not src.reviewed_by or src.reviewed_on is None):
            out.append(Problem("unreviewed", src.id, "scholar_approved needs reviewed_by and reviewed_on"))
        if (
            src.kind in ("hadith", "dua")
            and at_least(src.status, "text_verified")
            and not src.approved_sha256
        ):
            out.append(Problem("no-hash", src.id, "a verified/approved text needs approved_sha256"))
        cand = resolver.candidates.get(src.id)
        if cand is not None and cand.reference_check != "matched":
            out.append(
                Problem("candidate", src.id, f"the fetched reference is {cand.reference_check}", "warning")
            )
    return out


# ---- the print gate -------------------------------------------------------------------------------------


def chain(resolver: Resolver, source_id: str) -> list[str]:
    """`source_id` and the sources it stands on (a dua's hadith, a ruling's basis)."""
    out, todo = [], [source_id]
    while todo:
        current = todo.pop()
        src = resolver.register.by_id.get(current)
        if src is None or current in out:
            continue
        out.append(current)
        todo += [*src.basis, *([src.dua.from_] if src.dua else [])]
    return out


def check_print(pages: Iterable[Mapping[str, Any]], resolver: Resolver) -> list[Problem]:
    """A print build fails on any placeholder and on any source that is not approved (`APPROVED`)."""
    out: list[Problem] = []
    for page in pages:
        pid = str(page.get("id", "?"))
        for req in wording_requests(page):
            if req.source not in resolver.register.by_id:
                continue  # reported as unknown-source
            try:
                got = resolver.resolve(req.source, req.span)
            except SourceError as err:
                out.append(Problem("marker", pid, f"{req.path}: {err}"))
                continue
            if got.text is None:
                out.append(
                    Problem(
                        "placeholder", pid, f"{req.path}: {req.source} has no wording ({got.placeholder})"
                    )
                )
        checked: set[str] = set()
        for source_id in page_ids(page):
            for each in chain(resolver, source_id):  # a dua stands on its hadith, a ruling on its basis
                status = resolver.status_of(each)
                if status not in APPROVED and each not in checked and each in resolver.register.by_id:
                    out.append(Problem("not-approved", pid, f"{each} is {status}, not approved"))
                checked.add(each)
    return out


# ---- the scholar's queue --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    source: str  # the source id the question is about
    pages: tuple[str, ...]  # the pages that use it (empty: planned for the volumes)
    question: str
    status: str


def scholar_queue(resolver: Resolver, pages: Iterable[Mapping[str, Any]] = ()) -> list[Decision]:
    """Every open `scholar_decision`: the source, the pages that use it (a dua's question also reaches the
    pages that print its hadith's text) and the question. Approved sources are no longer open."""
    used: dict[str, list[str]] = {}
    for page in pages:
        pid = str(page.get("id", "?"))
        for source_id in page_ids(page):
            for each in chain(resolver, source_id):
                if pid not in used.setdefault(each, []):
                    used[each].append(pid)
    out = []
    for src in resolver.register.sources:
        if src.scholar_decision and not src.decided:
            out.append(Decision(src.id, tuple(used.get(src.id, ())), src.scholar_decision, src.status))
    return out
