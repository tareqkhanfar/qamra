"""«قلبي يعرف الله» (Addendum 10 §3): the register of religious sources, and the one way their wording
reaches a page.

    uv run python -m qamra_workbook.islamic_sources check [--print]     # problems of the register and the
    sample pages
    uv run python -m qamra_workbook.islamic_sources status [--decisions]  # counts per status, open scholar
    decisions

THE RULE: no religious wording is typed or generated. `content/islamic/sources.yaml` and `sources.d/*.yaml`
hold
REFERENCES; a page asks for wording by a source id and `Resolver.resolve` copies it from a corpus:

  quran   the Tanzil Uthmani file (`surah|ayah|text` lines, `#` header lines kept for the licence note);
  hadith  `content/islamic/candidates.json` (written by `scripts/islamic_sources.py fetch`): a CANDIDATE only;
  dua     a span of a hadith's text between two markers (inclusive); the markers are matched on the letters
  only
          (harakat, tatweel, punctuation and spacing ignored, alef and hamza forms folded) and are never
          printed:
          what is returned is the ORIGINAL slice with its harakat, and a marker that is not found raises;
  sira / ruling   reference only: the scholar supplies the source; there is never any text to print.

Status ladder (`STATUSES`, advancing only forward): proposed → text_candidate → text_verified →
scholar_approved.
A preview build may print candidates and marked placeholders; a print build needs every source it uses at
`scholar_approved` and no placeholder (`islamic_checks.check_print`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

REPO = Path(__file__).resolve().parents[4]
SOURCES = REPO / "content/islamic/sources.yaml"
CANDIDATES = REPO / "content/islamic/candidates.json"
SAMPLES = REPO / "content/islamic/samples.yaml"
PLAN = REPO / "content/islamic/plan.yaml"
VOLUMES = REPO / "content/islamic/volumes"

Status = Literal["proposed", "text_candidate", "text_verified", "scholar_approved"]
STATUSES: tuple[Status, ...] = ("proposed", "text_candidate", "text_verified", "scholar_approved")
Kind = Literal["quran", "hadith", "dua", "sira", "ruling"]
KINDS: tuple[Kind, ...] = ("quran", "hadith", "dua", "sira", "ruling")
TEXT_KINDS: frozenset[str] = frozenset({"quran", "hadith", "dua"})  # the kinds that can have wording
Check = Literal["matched", "mismatch", "not_found"]
# a typed text that holds this many letters of a register wording in a row is religious wording typed by hand
MIN_WORDING_LETTERS = 7

# What a marked placeholder block says when a source has no verified text yet (a note to the printer, never
# religious wording). The reason it is missing is kept apart, in `Resolved.placeholder`.
NOTICE: dict[str, str] = {
    "quran": "نصّ الآية يُنسخ من ملف طنزيل المعتمد عند الطباعة",
    "hadith": "نصّ الحديث يُنسخ من المصدر المعتمد عند الطباعة",
    "dua": "نصّ الذكر يُنسخ من المصدر المعتمد عند الطباعة",
}
# Names of the collections for the citation line printed under a quotation (bibliographic labels).
COLLECTION_AR: dict[str, str] = {
    "bukhari": "صحيح البخاري",
    "muslim": "صحيح مسلم",
    "abudawud": "سنن أبي داود",
    "tirmidhi": "سنن الترمذي",
    "nasai": "سنن النسائي",
    "ibnmajah": "سنن ابن ماجه",
    "malik": "موطأ مالك",
    "adabmufrad": "الأدب المفرد",
}


class SourceError(ValueError):
    """The register or a corpus is wrong, or a marker was not found: the build stops (never a silent
    guess).
    """


# ---- the register's schema ------------------------------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class QuranRef(_Model):
    surah: int = Field(ge=1, le=114)
    from_: int = Field(alias="from", ge=1)
    to: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> QuranRef:
        if self.to < self.from_:
            raise ValueError("`to` is before `from`")
        return self


class HadithRef(_Model):
    collection: str
    number: int = Field(ge=1)


class DuaRef(_Model):
    from_: str = Field(alias="from")  # the id of the hadith this span is cut from
    start: str
    end: str


class Source(_Model):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    kind: Kind
    title_ar: str
    topic: str = ""
    quran: QuranRef | None = None
    hadith: HadithRef | None = None
    dua: DuaRef | None = None
    basis: list[str] = Field(default_factory=list)  # a `ruling`'s hadith/verse ids; it has no text of its own
    expect: list[str] = Field(default_factory=list)  # sanity keywords the fetched hadith must contain
    grading_claimed: str = ""  # the drafter's belief; the scholar verifies it
    scholar_decision: str = (
        ""  # a point where scholars differ or the age needs care: goes to the review queue
    )
    status: Status = "proposed"
    reviewed_by: str = ""
    reviewed_on: date | None = None
    # the sha256 of the wording the scholar saw (hadith, dua): a later fetch that changes it fails loudly
    approved_sha256: str = ""

    @model_validator(mode="after")
    def _shape(self) -> Source:
        need = {"quran": self.quran, "hadith": self.hadith, "dua": self.dua}
        for kind, block in need.items():
            if self.kind == kind and block is None:
                raise ValueError(f"a {kind} source needs a `{kind}:` block")
            if self.kind != kind and block is not None:
                raise ValueError(f"a {self.kind} source must not have a `{kind}:` block")
        if self.basis and self.kind != "ruling":
            raise ValueError("`basis` belongs to a ruling")
        return self

    @property
    def decided(self) -> bool:
        return self.status == "scholar_approved"


class QuranCorpus(_Model):
    file: str
    license_note: str = ""
    sha256: str = ""  # when set, the file must have exactly this sha256


class HadithCorpus(_Model):
    dataset: str
    editions: dict[str, str] = Field(default_factory=dict)


class Corpus(_Model):
    quran: QuranCorpus
    hadith: HadithCorpus


@dataclass(frozen=True)
class Register:
    """Every source of sources.yaml and sources.d/*.yaml, by id, with the file each came from."""

    sources: tuple[Source, ...]
    corpus: Corpus
    origin: Mapping[str, str] = field(default_factory=dict)  # source id → file name
    root: Path = REPO

    def __post_init__(self) -> None:
        seen: dict[str, str] = {}
        for src in self.sources:
            if src.id in seen:
                where = self.origin.get(src.id, "?")
                raise SourceError(f"duplicate source id {src.id!r} (in {where} and in {seen[src.id]})")
            seen[src.id] = self.origin.get(src.id, "?")

    @property
    def by_id(self) -> dict[str, Source]:
        return {s.id: s for s in self.sources}

    def get(self, source_id: str) -> Source:
        found = self.by_id.get(source_id)
        if found is None:
            raise SourceError(f"unknown source id {source_id!r}")
        return found

    def of_kind(self, kind: str) -> list[Source]:
        return [s for s in self.sources if s.kind == kind]

    @classmethod
    def from_dicts(cls, main: Mapping[str, Any], *more: Mapping[str, Any], root: Path = REPO) -> Register:
        """A register from already-parsed documents: the main one (with `corpus`) and extra source lists."""
        rows = [*main.get("sources", []), *(r for doc in more for r in doc.get("sources", []))]
        sources = tuple(_validated(r, "memory") for r in rows)
        return cls(sources, Corpus.model_validate(main["corpus"]), {}, root)


def _validated(row: Any, name: str) -> Source:
    try:
        return Source.model_validate(row)
    except ValidationError as err:
        who = row.get("id", "?") if isinstance(row, dict) else "?"
        first = err.errors()[0]
        loc = ".".join(str(p) for p in first["loc"])
        raise SourceError(f"{name}: source {who!r}: {loc}: {first['msg']}") from None


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        mark = getattr(err, "problem_mark", None)
        where = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        problem = getattr(err, "problem", None) or "YAML error"
        raise SourceError(f"{path.name}{where}: {problem}") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise SourceError(f"{path.name}: a top-level `sources:` list is required")
    return raw


def load(path: Path = SOURCES, root: Path = REPO) -> Register:
    """sources.yaml (its `corpus` and sources) merged with every sources.d/*.yaml next to it, sorted by file
    name. Ids must be unique across all files; any malformed file or row raises `SourceError` naming it."""
    main = _read_yaml(path)
    unknown = set(main) - {"version", "corpus", "sources"}
    if unknown:
        raise SourceError(f"{path.name}: unknown top-level keys {sorted(unknown)}")
    if "corpus" not in main:
        raise SourceError(f"{path.name}: `corpus:` is required")
    sources: list[Source] = []
    origin: dict[str, str] = {}
    files = [path, *sorted((path.parent / "sources.d").glob("*.yaml"))]
    for file in files:
        doc = main if file == path else _read_yaml(file)
        extra = set(doc) - {"version", "sources"} - ({"corpus"} if file == path else set())
        if extra:
            raise SourceError(f"{file.name}: unknown top-level keys {sorted(extra)}")
        for row in doc["sources"]:
            src = _validated(row, file.name)
            if src.id in origin:
                raise SourceError(f"duplicate source id {src.id!r} (in {file.name} and in {origin[src.id]})")
            origin[src.id] = file.name
            sources.append(src)
    try:
        corpus = Corpus.model_validate(main["corpus"])
    except ValidationError as err:
        raise SourceError(f"{path.name}: corpus: {err.errors()[0]['msg']}") from None
    return Register(tuple(sources), corpus, origin, root)


# ---- matching on the letters only -----------------------------------------------------------------------

# alef and hamza forms, alef maksura, teh marbuta: folded so that the orthography of a marker and of the text
# (Uthmani, plain, a collection's own) never decides whether it matches. A lone hamza is dropped.
_FOLD = str.maketrans("أإآٱىةؤئ", "اااايهوي")
_LETTER_CATEGORIES = frozenset({"Lo", "Ll", "Lu", "Lt"})  # not Lm: tatweel and the Quranic small letters


def letters_map(text: str) -> tuple[str, list[int]]:
    """`text` reduced to its folded letters, and for each kept letter its index in `text`."""
    kept: list[str] = []
    index: list[int] = []
    for i, original in enumerate(text):
        for ch in unicodedata.normalize("NFKC", original):  # ﷲ and ﷺ expand to their letters
            ch = ch.translate(_FOLD)
            if ch != "ء" and unicodedata.category(ch) in _LETTER_CATEGORIES:
                kept.append(ch)
                index.append(i)
    return "".join(kept), index


def letters(text: str) -> str:
    """The folded letters of `text`: what markers are compared on."""
    return letters_map(text)[0]


@dataclass(frozen=True)
class Span:
    """The words of a text from `start` to `end` inclusive (search markers: never printed)."""

    start: str
    end: str

    @classmethod
    def of(cls, raw: Mapping[str, Any] | Span) -> Span:
        if isinstance(raw, Mapping):
            return cls(str(raw["start"]), str(raw["end"]))
        return cls(raw.start, raw.end)  # a Span (also one from this module run as __main__)


def cut(text: str, span: Span) -> tuple[str, int]:
    """The ORIGINAL slice of `text` (harakat kept) from the first match of `span.start` to the first match of
    `span.end` that finishes at or after the start marker's end (so the two markers may be the same words).
    Also returns how many places the start marker matches (the first is used). Raises `SourceError` when a
    marker is empty or not found."""
    folded, index = letters_map(text)
    first, last = letters(span.start), letters(span.end)
    if not first or not last:
        raise SourceError("a span marker has no letters")
    i = folded.find(first)
    if i < 0:
        raise SourceError(f"start marker {span.start!r} not found")
    j = i
    while True:
        j = folded.find(last, j)
        if j < 0:
            raise SourceError(f"end marker {span.end!r} not found after the start marker {span.start!r}")
        if j + len(last) >= i + len(first):
            break
        j += 1
    begin, stop = index[i], index[j + len(last) - 1] + 1
    while stop < len(text) and unicodedata.category(text[stop]) == "Mn":  # the harakat of the last letter
        stop += 1
    return text[begin:stop], folded.count(first)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- the corpora ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class QuranFile:
    """A Tanzil text file: `surah|ayah|text` lines; the `#` header (its licence) is kept."""

    name: str
    sha: str
    header: tuple[str, ...]
    ayat: Mapping[tuple[int, int], str]

    def lines(self, surah: int, first: int, last: int) -> tuple[tuple[int, str], ...]:
        out = []
        for n in range(first, last + 1):
            text = self.ayat.get((surah, n))
            if text is None:
                raise SourceError(f"{surah}:{n} is not in {self.name}")
            out.append((n, text))
        return self._basmala_apart(tuple(out), surah)

    def _basmala_apart(self, lines: tuple[tuple[int, str], ...], surah: int) -> tuple[tuple[int, str], ...]:
        """Tanzil prints the basmala inside the first ayah of every surah but al-Fatiha; it is not an ayah
        there, so it is split off as its own unnumbered line (number 0). Only the exact basmala text of 1:1
        is split off; nothing is rewritten."""
        basmala = self.ayat.get((1, 1))
        if not basmala or surah == 1 or not lines or lines[0][0] != 1:
            return lines
        first = lines[0][1]
        if first.startswith(basmala + " ") and len(first) > len(basmala) + 1:
            return ((0, basmala), (1, first[len(basmala) :].strip()), *lines[1:])
        return lines


def parse_quran(raw: str, name: str = "quran-uthmani.txt") -> QuranFile:
    header: list[str] = []
    ayat: dict[tuple[int, int], str] = {}
    for number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        if line.startswith("#"):
            header.append(line[1:].strip())
            continue
        parts = line.split("|", 2)
        if len(parts) != 3 or not parts[0].strip().isdigit() or not parts[1].strip().isdigit():
            raise SourceError(f"{name} line {number}: expected `surah|ayah|text`")
        ayat[(int(parts[0]), int(parts[1]))] = parts[2].strip()
    if not ayat:
        raise SourceError(f"{name}: no ayat found")
    return QuranFile(name, hashlib.sha256(raw.encode("utf-8")).hexdigest(), tuple(header), ayat)


def read_quran(path: Path, expected_sha256: str = "") -> QuranFile | None:
    """The Tanzil file, or None while it is not there (pages print a marked placeholder)."""
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    parsed = parse_quran(raw, path.name)
    if expected_sha256 and parsed.sha != expected_sha256:
        raise SourceError(
            f"{path.name}: sha256 {parsed.sha[:12]}… is not the {expected_sha256[:12]}… recorded"
        )
    return parsed


@dataclass(frozen=True)
class Candidate:
    """A hadith (or the trial span of a dua) fetched from an open dataset: a candidate, never approved."""

    id: str
    kind: str
    text: str
    sha: str
    reference_check: Check
    dataset: str = ""
    edition: str = ""
    number: int | None = None  # the register's number of the hadith
    dataset_number: int | None = None  # its number in the dataset's files, when that differs
    numbering: str = ""  # hadithnumber | arabicnumber: which of the dataset's two numbers matched
    grades: tuple[Mapping[str, Any], ...] = ()
    missing: tuple[str, ...] = ()
    note: str = ""

    @classmethod
    def of(cls, raw: Mapping[str, Any]) -> Candidate:
        text = str(raw.get("text", ""))
        return cls(
            id=str(raw["id"]),
            kind=str(raw.get("kind", "hadith")),
            text=text,
            sha=str(raw.get("sha256") or sha256(text)),
            reference_check=raw.get("reference_check", "not_found"),
            dataset=str(raw.get("dataset", "")),
            edition=str(raw.get("edition", "")),
            number=raw.get("number"),
            dataset_number=raw.get("dataset_number"),
            numbering=str(raw.get("numbering", "")),
            grades=tuple(raw.get("grades", ())),
            missing=tuple(raw.get("missing", ())),
            note=str(raw.get("note", "")),
        )


def read_candidates(path: Path = CANDIDATES) -> dict[str, Candidate]:
    """content/islamic/candidates.json: {"entries": {id: {...}}}. A missing file means none were fetched."""
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {k: Candidate.of(v) for k, v in raw.get("entries", {}).items()}
    except (ValueError, KeyError, TypeError) as err:
        raise SourceError(f"{path.name}: {err}") from None


# ---- resolving a source id to what may be printed -------------------------------------------------------


def at_least(status: Status, floor: Status) -> bool:
    return STATUSES.index(status) >= STATUSES.index(floor)


def _higher(a: Status, b: Status) -> Status:
    return a if at_least(a, b) else b


@dataclass(frozen=True)
class Resolved:
    """What a source id gives a page: the wording with its provenance, or why there is none (a marked
    placeholder block prints `notice`)."""

    id: str
    kind: str
    title_ar: str
    status: Status  # the effective status (declared, raised by the corpus the wording came from)
    text: str | None  # None: no wording to print
    lines: tuple[tuple[int, str], ...] = ()  # (ayah, text) for a Quran range; ((0, text),) otherwise
    provenance: str = ""
    placeholder: str = ""  # why there is no text; "" when there is
    notice: str = ""  # the placeholder block's visible text
    reference: str = ""  # the citation: «21:87» or «صحيح البخاري 6094» (digits are the page's to format)
    text_expected: bool = True  # False for sira / ruling: reference only, nothing to print
    scholar_decision: str = ""

    @property
    def has_text(self) -> bool:
        return self.text is not None

    @property
    def printable(self) -> bool:
        """True when a print build may use it: wording present and approved by the scholar."""
        return self.has_text and self.status == "scholar_approved"


class Resolver:
    """Source id → `Resolved`, from the register and its corpora (the Tanzil file, the fetched candidates)."""

    def __init__(
        self,
        register: Register,
        quran: QuranFile | None = None,
        candidates: Mapping[str, Candidate] | None = None,
    ) -> None:
        self.register = register
        self.quran = quran
        self.candidates: Mapping[str, Candidate] = candidates or {}
        self._base: dict[str, Resolved] = {}
        self._wordings: list[tuple[str, str]] | None = None

    @classmethod
    def load(cls, path: Path = SOURCES, candidates: Path = CANDIDATES, root: Path = REPO) -> Resolver:
        register = load(path, root)
        corpus = register.corpus.quran
        return cls(register, read_quran(root / corpus.file, corpus.sha256), read_candidates(candidates))

    def known(self, source_id: str) -> bool:
        return source_id in self.register.by_id

    def status_of(self, source_id: str) -> Status:
        return self._resolve_base(source_id).status

    def wordings(self) -> list[tuple[str, str]]:
        """(source id, letters) of every dhikr and every Quran ayah whose wording the register can give:
        what a text
        typed by hand must never contain (a verse or a dhikr reaches a page only through its source id)."""
        if self._wordings is None:
            found: list[tuple[str, str]] = []
            for src in self.register.sources:
                if src.kind not in ("dua", "quran"):
                    continue
                try:
                    got = self._resolve_base(src.id)
                except SourceError:
                    continue  # a failing marker is reported by the register check
                if got.text is None:
                    continue
                pieces = [t for _, t in got.lines] if src.kind == "quran" else [got.text]
                found += [
                    (src.id, folded)
                    for piece in pieces
                    if len(folded := letters(piece)) >= MIN_WORDING_LETTERS
                ]
            self._wordings = found
        return self._wordings

    def resolve(self, source_id: str, span: Span | Mapping[str, Any] | None = None) -> Resolved:
        """The source's wording, or a placeholder; with `span`, only the words between its markers
        (inclusive).
        Raises `SourceError` for an unknown id, a marker that is not found, or text that changed after the
        scholar saw it."""
        base = self._resolve_base(source_id)
        if span is None or base.text is None:
            return base
        words, _ = cut(base.text, Span.of(span))
        provenance = f"{base.provenance} · words cut between two markers"
        return replace(base, text=words, lines=((0, words),), provenance=provenance)

    # -- one source, whole --------------------------------------------------------------------------------

    def _resolve_base(self, source_id: str) -> Resolved:
        if source_id not in self._base:
            src = self.register.get(source_id)
            match src.kind:
                case "quran":
                    self._base[source_id] = self._quran(src)
                case "hadith":
                    self._base[source_id] = self._hadith(src)
                case "dua":
                    self._base[source_id] = self._dua(src)
                case _:
                    self._base[source_id] = self._reference_only(src)
        return self._base[source_id]

    def _make(self, src: Source, **fields: Any) -> Resolved:
        return Resolved(
            id=src.id,
            kind=src.kind,
            title_ar=src.title_ar,
            scholar_decision=src.scholar_decision,
            text_expected=src.kind in TEXT_KINDS,
            **fields,
        )

    def _missing(self, src: Source, reason: str, reference: str = "") -> Resolved:
        return self._make(
            src,
            status=src.status,
            text=None,
            placeholder=reason,
            notice=NOTICE.get(src.kind, ""),
            reference=reference,
        )

    def _reference_only(self, src: Source) -> Resolved:
        return self._make(
            src, status=src.status, text=None, placeholder="reference only: the scholar supplies the source"
        )

    def _quran(self, src: Source) -> Resolved:
        ref = src.quran
        assert ref is not None
        span = f"{ref.surah}:{ref.from_}" + (f"-{ref.to}" if ref.to != ref.from_ else "")
        if self.quran is None:
            return self._missing(
                src, f"the Tanzil file ({self.register.corpus.quran.file}) is not there", span
            )
        lines = self.quran.lines(ref.surah, ref.from_, ref.to)
        return self._make(
            src,
            status=_higher(src.status, "text_verified"),  # copied verbatim from the licensed file
            text=" ".join(t for _, t in lines),
            lines=lines,
            provenance=f"Tanzil · {self.quran.name} · sha256 {self.quran.sha[:12]} · {span}",
            reference=span,
        )

    def _hadith(self, src: Source) -> Resolved:
        ref = src.hadith
        assert ref is not None
        label = f"{COLLECTION_AR.get(ref.collection, ref.collection)} {ref.number}"
        cand = self.candidates.get(src.id)
        if cand is None:
            return self._missing(src, "no candidate fetched (scripts/islamic_sources.py fetch)", label)
        if cand.reference_check != "matched":
            note = f" ({cand.note})" if cand.note else ""
            return self._missing(src, f"reference check {cand.reference_check}{note}", label)
        if at_least(src.status, "text_verified") and src.approved_sha256 and src.approved_sha256 != cand.sha:
            raise SourceError(f"{src.id}: the text changed since it was verified (sha256 differs)")
        return self._make(
            src,
            status=_higher(src.status, "text_candidate"),
            text=cand.text,
            lines=((0, cand.text),),
            provenance=(
                f"{cand.dataset} · {cand.edition} · {cand.dataset_number or cand.number}"
                f"{' (' + cand.numbering + ')' if cand.numbering == 'arabicnumber' else ''} "
                f"· sha256 {cand.sha[:12]}"
            ),
            reference=label,
        )

    def _dua(self, src: Source) -> Resolved:
        ref = src.dua
        assert ref is not None
        parent = self.register.get(ref.from_)
        if parent.kind != "hadith":
            raise SourceError(f"{src.id}: `dua.from` {ref.from_!r} is a {parent.kind}, not a hadith")
        whole = self._resolve_base(ref.from_)
        if whole.text is None:
            return self._missing(
                src, f"its hadith {ref.from_} has no text ({whole.placeholder})", whole.reference
            )
        try:
            words, _ = cut(whole.text, Span(ref.start, ref.end))
        except SourceError as err:
            raise SourceError(f"{src.id}: {err}") from None
        return self._make(
            src,
            status=_higher(src.status, "text_candidate"),
            text=words,
            lines=((0, words),),
            provenance=f"{whole.provenance} · words cut between two markers",
            reference=whole.reference,
        )


# ---- the command line -----------------------------------------------------------------------------------


def _print_problems(problems: Iterable[Any], strict: bool) -> bool:
    """Print the problems (errors first); True when the build passes."""
    found = sorted(problems, key=lambda p: (p.level != "error", p.code, p.where))
    for problem in found:
        print(problem)
    failed = [p for p in found if p.level == "error" or strict]
    print(f"{len(failed)} problem(s)" if failed else "ok: no problems", end="")
    warnings = len(found) - len([p for p in found if p.level == "error"])
    print(f" ({warnings} warning(s))" if warnings else "")
    return not failed


def _table(rows: list[list[str]]) -> str:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)).rstrip() for r in rows)


def cmd_check(args: argparse.Namespace) -> int:
    from qamra_workbook import islamic_checks as checks

    resolver = Resolver.load()
    pages = checks.load_pages(args.samples) if args.samples.is_file() else []
    rules = checks.PageRules.load()
    problems = [*checks.check_register(resolver), *checks.check_pages(pages, resolver, rules)]
    if args.print_build:
        problems += checks.check_print(pages, resolver)
    mode = "print" if args.print_build else "preview"
    print(f"{len(resolver.register.sources)} sources, {len(pages)} pages, {mode} build")
    return 0 if _print_problems(problems, args.strict) else 1


def cmd_status(args: argparse.Namespace) -> int:
    from qamra_workbook import islamic_checks as checks

    resolver = Resolver.load()
    reg = resolver.register
    pages = checks.load_pages(args.samples) if args.samples.is_file() else []
    counts = Counter((s.kind, resolver.status_of(s.id)) for s in reg.sources)
    rows = [["kind", *STATUSES, "total"]]
    for kind in KINDS:
        have = [counts[(kind, st)] for st in STATUSES]
        if sum(have):
            rows.append([kind, *map(str, have), str(sum(have))])
    rows.append(
        ["all", *(str(sum(counts[(k, st)] for k in KINDS)) for st in STATUSES), str(len(reg.sources))]
    )
    print(_table(rows))
    quran = resolver.quran
    print(
        f"\nQuran file: "
        f"{'present, ' + quran.name if quran else ('NOT there: pages print a marked placeholder')}"
    )
    cands = Counter(c.reference_check for c in resolver.candidates.values() if c.kind == "hadith")
    hadith = reg.of_kind("hadith")
    print(
        f"hadith candidates: {sum(cands.values())} fetched of {len(hadith)} hadith: "
        + ", ".join(f"{k} {n}" for k, n in sorted(cands.items()))
    )
    queue = checks.scholar_queue(resolver, pages)
    print(f"open scholar decisions: {len(queue)}")
    if args.decisions:
        for d in queue:
            where = ", ".join(d.pages) or "volumes"
            print(f"  - {d.source} [{where}]: {d.question}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="problems of the register and the sample pages")
    check.add_argument(
        "--print", action="store_true", dest="print_build", help="a print build: no placeholder, all approved"
    )
    check.add_argument("--strict", action="store_true", help="warnings fail too")
    check.add_argument("--samples", type=Path, default=SAMPLES)
    check.set_defaults(run=cmd_check)
    status = sub.add_parser("status", help="counts per status and the open scholar decisions")
    status.add_argument("--decisions", action="store_true", help="list every open decision")
    status.add_argument("--samples", type=Path, default=SAMPLES)
    status.set_defaults(run=cmd_status)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return int(args.run(args))
    except SourceError as err:
        print(f"✗ {err}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
