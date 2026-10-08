"""Digital delivery (docs/plans/digital-delivery.md): which lines a parent downloads, when, and which files.

Shared by the API (`routers/downloads.py`: the parent's list, the file's state and the file itself) and
the worker (`jobs/downloads.py`: the home-print PDFs and the "ready to download" email). Pure functions: the
callers load the rows (async or sync) and read storage themselves.

**What is downloadable** (the catalog and the addenda):
- every line whose variant is `format: digital`: «نسخة رقمية» of a story (Classic) and «ملف PDF» of the
  activity books (a volume, a stage, the family book, a set). The file is the whole book with its cover, cut
  for home printing, plus the extra files the book's job renders (the answer key; the family book's sticker
  and card sheets), since a digital buyer gets no printed insert.
- a printed «رحلتي الأولى» line: only its answer key, a free download (Addendum 6 §5).
- every other printed line: nothing. The free «نسخة رقمية مع المطبوع» is the web reader (owner's audit,
  2026-10-07), and a PDF of the printed book would undercut the digital variants.

**When** (the same gates as the reader and the print approval):
- a story: once staff confirmed its words («تأكيد النص واعتماد الكتاب»: approved, ordered or printed);
- an activity book: once its render passed (in review with every preflight passed and no flag a reviewer must
  look at), or once an admin approved it;
- a set: each volume as soon as it is ready; the line is ready (and emailed) when every volume is;
- the order is confirmed and not cancelled; the child's data was not deleted.
"""

import hashlib
import re
import unicodedata
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import Select, or_, select

from qamra_core.db.models import Book, BookStatus, OrderItem, OrderStatus
from qamra_core.islamic_review import VOLUME_NAMES_AR, volumes_of

STORY_LINES = ("classic", "magic")
ACTIVITY_LINES = ("family", "journey", "islamic", "workbook")
DIGITAL = "digital"
LIVE_ORDERS = frozenset(
    {
        OrderStatus.confirmed,
        OrderStatus.generating,
        OrderStatus.review,
        OrderStatus.printing,
        OrderStatus.shipped,
        OrderStatus.delivered,
        OrderStatus.reprint,
    }
)
LISTED_ORDERS = LIVE_ORDERS | {OrderStatus.new}  # a new order's line shows as "preparing"
FINAL = frozenset({BookStatus.approved, BookStatus.ordered, BookStatus.printed})
# flags that wait for a person before a family gets the file (the same ones the reviewer sees before print)
HELD_FLAGS = frozenset(
    {
        "preflight_failed",
        "scholar_review",
        "pages_missing",
        "text_changed",
        "name_en_guessed",
        "name_not_traceable",
    }
)
BOOK = "book"
# the extra files a book's job stores in `generation["files"]`, in the order they are listed
EXTRAS = ("answer-key", "stickers", "card-money-recipes", "card-games-roles")
FREE_EXTRAS: dict[str, tuple[str, ...]] = {"journey": ("answer-key",)}  # Addendum 6 §5: also for print
KINDS = (BOOK, *EXTRAS)
SETS = {"journey": ("1", "2", "3"), "workbook": ("1", "2", "3")}
Lang = Literal["ar", "en"]


# ---- the line --------------------------------------------------------------------------------------------


def options_of(item: OrderItem) -> dict[str, str]:
    options = (item.title or {}).get("options") or {}
    out = {str(k): str(v) for k, v in options.items()}
    if "format" not in out and item.product is not None:  # lines from before the catalog
        out["format"] = item.product.value
    return out


def is_digital(options: Mapping[str, str]) -> bool:
    return options.get("format") == DIGITAL


def offers_download(line: str | None, options: Mapping[str, str]) -> bool:
    """Whether a line of this product and variant ever has a file for the parent (see the module's doc)."""
    if line not in (*STORY_LINES, *ACTIVITY_LINES):
        return False
    return is_digital(options) or line in FREE_EXTRAS


def sold_as_file(item: OrderItem) -> bool:
    """A digital line: the file is what was bought (the order page's download button, the email)."""
    options = options_of(item)
    return is_digital(options) and offers_download(item.line, options)


def parts_of(line: str | None, options: Mapping[str, str]) -> tuple[str, ...]:
    """The books a line is made of: its volumes or stages (every one for a set), or one book ("")."""
    if line == "islamic":
        return volumes_of(options.get("volume"))
    if line in SETS:
        raw = str(options.get("stage" if line == "journey" else "volume") or "").strip().lower()
        if raw == "set":
            return SETS[line]
        if raw in SETS[line]:
            return (raw,)
        return ("1",) if line == "journey" else ()  # the journey job's default stage
    return ("",)


def part_of(line: str | None, book: Book) -> str:
    gen = book.generation or {}
    if line == "journey":
        return str(gen.get("stage") or "")
    if line in ("islamic", "workbook"):
        return str(gen.get("volume") or "")
    return ""


def owned_by(book: Book, item: OrderItem) -> bool:
    """A book belongs to this line (the query is the caller's; this guards what it loaded)."""
    if item.line in STORY_LINES:
        return book.id == item.book_id
    gen = book.generation or {}
    return gen.get("order_item_id") == str(item.id) and gen.get("line") == item.line


def books_query(items: Iterable[OrderItem]) -> Select[Book] | None:
    """The books made for these lines (async or sync session): a story's on the line, an activity book's by
    `generation.order_item_id`. None when no line has any."""
    lines = list(items)
    story = [i.book_id for i in lines if i.line in STORY_LINES and i.book_id]
    activity = [str(i.id) for i in lines if i.line in ACTIVITY_LINES]
    if not story and not activity:
        return None
    return select(Book).where(or_(Book.id.in_(story), Book.generation["order_item_id"].astext.in_(activity)))


# ---- readiness -----------------------------------------------------------------------------------------


def _preflight_passed(preflight: Mapping[str, Any] | None) -> bool:
    reports = [r for r in (preflight or {}).values() if isinstance(r, Mapping)]
    return bool(reports) and all(bool(r.get("passed")) for r in reports)


def book_ready(line: str | None, book: Book) -> bool:
    """Whether the family may download this book now (see the module's doc)."""
    if not book.pdf_interior_key:
        return False
    if book.status in FINAL:
        return True
    if line not in ACTIVITY_LINES:
        return False  # a story waits for staff to confirm its words
    flags = set(book.flags or [])
    return (
        book.status == BookStatus.in_review and not flags & HELD_FLAGS and _preflight_passed(book.preflight)
    )


def kinds_of(line: str | None, digital: bool, book: Book) -> list[str]:
    files = (book.generation or {}).get("files") or {}
    if digital:
        return [BOOK, *(k for k in EXTRAS if files.get(k))]
    return [k for k in FREE_EXTRAS.get(line or "", ()) if files.get(k)]


def sources_of(book: Book, kind: str) -> list[str]:
    """The print files a home file is made from (the cover only when the book has one)."""
    if kind == BOOK:
        return [k for k in (book.pdf_interior_key, book.pdf_cover_key) if k]
    key = ((book.generation or {}).get("files") or {}).get(kind)
    return [str(key)] if key else []


@dataclass(frozen=True)
class FileRef:
    book_id: uuid.UUID
    kind: str
    part: str  # "V1", "2", "" (one book)
    level: str  # «دوسية التأسيس»: kg1 / kg2


@dataclass
class LineState:
    ready: bool  # every book of the line can be downloaded
    parts_total: int
    parts_ready: int
    files: list[FileRef] = field(default_factory=list)  # the files of the ready books
    books: dict[uuid.UUID, Book] = field(default_factory=dict)  # the ready books, by id


def line_state(item: OrderItem, order_status: OrderStatus, books: Iterable[Book]) -> LineState:
    """What the line's parent can download now. `books` are the books made for the line (any status)."""
    options = options_of(item)
    digital = is_digital(options)
    wanted = parts_of(item.line, options)
    mine = [b for b in books if owned_by(b, item)]
    if order_status not in LIVE_ORDERS or not offers_download(item.line, options):
        return LineState(False, len(wanted), 0)
    by_part: dict[str, Book] = {}
    for made in sorted(mine, key=lambda b: b.created_at):  # a job ran again: the newest book of a part wins
        by_part[part_of(item.line, made)] = made
    state = LineState(False, len(wanted), 0)
    for part in wanted:
        book = by_part.get(part)
        if book is None or not book_ready(item.line, book):
            continue
        kinds = kinds_of(item.line, digital, book)
        if not kinds:
            continue
        state.parts_ready += 1
        state.books[book.id] = book
        level = str(options.get("level") or (book.generation or {}).get("level") or "")
        state.files += [FileRef(book.id, kind, part, level) for kind in kinds]
    state.ready = bool(wanted) and state.parts_ready == len(wanted)
    return state


def find_file(state: LineState, book_id: uuid.UUID, kind: str) -> FileRef | None:
    return next((f for f in state.files if f.book_id == book_id and f.kind == kind), None)


# ---- the cached home files ------------------------------------------------------------------------------


def home_prefix(book: Book) -> str:
    """Under the child's prefix, so «حذف كل بيانات طفلي» (one `delete_prefix`) removes these copies too."""
    return f"children/{book.child_id}/books/{book.id}/home/"


def version_of(etags: Sequence[str]) -> str:
    """The home copy's version: the print files it was cut from (a re-render makes a new one)."""
    return hashlib.sha256("|".join(etags).encode()).hexdigest()[:16]


def home_key(book: Book, kind: str, version: str) -> str:
    return f"{home_prefix(book)}{kind}/{version}.pdf"


def state_key(book_id: uuid.UUID | str, kind: str, version: str, what: Literal["prep", "failed"]) -> str:
    """Redis: a copy being made (`prep`) or one that could not be made (`failed`); ids only."""
    return f"dl:{what}:{book_id}:{kind}:{version}"


# ---- names ----------------------------------------------------------------------------------------------

PART_NAMES: dict[str, dict[str, dict[str, str]]] = {
    "islamic": {
        "ar": VOLUME_NAMES_AR,
        "en": {
            "V1": "Volume 1",
            "V2": "Volume 2",
            "V3": "Volume 3",
            "V4": "Volume 4",
            "V5": "Volume 5",
            "R": "Ramadan and Eid book",
        },
    },
    "journey": {
        "ar": {"1": "المحطة الأولى", "2": "المحطة الثانية", "3": "المحطة الثالثة"},
        "en": {"1": "Stage 1", "2": "Stage 2", "3": "Stage 3"},
    },
    "workbook": {
        "ar": {"1": "الجزء الأول", "2": "الجزء الثاني", "3": "الجزء الثالث"},
        "en": {"1": "Volume 1", "2": "Volume 2", "3": "Volume 3"},
    },
}
# short forms for file names, so a downloads folder sorts them: «قلبي-يعرف-الله-المجلد-1-ضحى.pdf»
PART_FILE: dict[str, dict[str, str]] = {
    "islamic": {"ar": "المجلد {n}", "en": "Volume {n}"},
    "journey": {"ar": "المحطة {n}", "en": "Stage {n}"},
    "workbook": {"ar": "الجزء {n}", "en": "Volume {n}"},
}
RAMADAN_FILE = {"ar": "رمضان والعيد", "en": "Ramadan and Eid"}
KIND_NAMES: dict[str, dict[str, str]] = {
    "answer-key": {"ar": "مفتاح الإجابات", "en": "Answer key"},
    "stickers": {"ar": "ورقة الملصقات", "en": "Sticker sheet"},
    "card-money-recipes": {"ar": "بطاقات النقود والوصفات", "en": "Money and recipe cards"},
    "card-games-roles": {"ar": "بطاقات الألعاب والأدوار", "en": "Game and role cards"},
}
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # تشكيل and تطويل
_NOT_NAME = re.compile(r"[^\w]+")


def part_name(line: str | None, part: str, lang: Lang) -> str:
    return PART_NAMES.get(line or "", {}).get(lang, {}).get(part, part)


def _part_file(line: str | None, part: str, lang: Lang) -> str:
    if not part:
        return ""
    if line == "islamic" and part == "R":
        return RAMADAN_FILE[lang]
    pattern = PART_FILE.get(line or "", {}).get(lang)
    return pattern.format(n=part.lstrip("Vv")) if pattern else part


def _slug(text: str) -> str:
    """Letters and digits of any script, joined by hyphens; no تشكيل, no characters a file system refuses."""
    plain = _DIACRITICS.sub("", unicodedata.normalize("NFC", text))
    return _NOT_NAME.sub("-", plain).strip("-_")


def line_title(item: OrderItem, child_name: str, books: Sequence[Book], lang: Lang) -> str:
    """The line in a few words (the email): a story's title, or the product with the volume and the child."""
    name = str((item.title or {}).get("name_ar" if lang == "ar" else "name_en") or item.sku or "")
    if item.line in STORY_LINES:
        title = next((b.title for b in books if b.title), None)
        return title or (f"{name} · {child_name}" if child_name else name)
    parts = parts_of(item.line, options_of(item))
    words = [name]
    if len(parts) == 1 and parts[0]:
        words.append(part_name(item.line, parts[0], lang))
    if child_name:
        words.append(child_name)
    return " · ".join(w for w in words if w)


def file_name(
    item: OrderItem, order_code: str, ref: FileRef, book: Book, child_name: str, lang: Lang
) -> tuple[str, str]:
    """The file's name as it downloads (UTF-8) and an ASCII fallback for old browsers.

    «قلبي-يعرف-الله-المجلد-1-ضحى.pdf», «مفتاح-الإجابات-رحلتي-الأولى-للتعلم-المحطة-2-ضحى.pdf»,
    «يوم-تخرج-ضحى.pdf».
    """
    product = str((item.title or {}).get("name_ar" if lang == "ar" else "name_en") or "")
    if item.line in STORY_LINES:
        title = book.title or product
        words = [title] + ([child_name] if child_name and child_name not in title else [])
    else:
        words = [product]
        if ref.level and item.line == "workbook":
            words.append(ref.level.upper())
        words += [_part_file(item.line, ref.part, lang), child_name]
    if ref.kind != BOOK:
        words.insert(0, KIND_NAMES.get(ref.kind, {}).get(lang, ref.kind))
    stem = "-".join(s for s in (_slug(w) for w in words if w) if s) or "qamra"
    ascii_parts = ["qamra", order_code, ref.level, ref.part, "" if ref.kind == BOOK else ref.kind]
    fallback = "-".join(_slug(p).lower() for p in ascii_parts if p and _slug(p).isascii())
    return f"{stem[:150]}.pdf", f"{fallback}.pdf"
