"""Book codes («QB-7K4M2», qamra_core.book_codes): the format, a code for every new book whatever creates it,
a drawn code that is taken is drawn again, a code is never given twice (not even after the book is deleted),
and the migration gives every existing book one (8c3f5a1d7e42)."""

import importlib.util
import itertools
import re
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from qamra_core import book_codes
from qamra_core.book_codes import ALPHABET, CODE_RE, CodeExhausted, code_filter, generate, is_code, normalize
from qamra_core.db.models import Book, BookCode, Child, Gender, Locale, Theme
from qamra_core.migrations import MIGRATIONS_DIR

CONFUSABLE = set("01OILBGSZQUV")


def test_the_format_reads_aloud_without_confusion() -> None:
    codes = {generate() for _ in range(3000)}
    assert len(codes) > 2990  # 8 million codes: a repeat in 3000 draws is rare
    for code in codes:
        assert CODE_RE.fullmatch(code) and len(code) == 8 and code.startswith("QB-")
        assert not set(code[3:]) & CONFUSABLE
    assert not set(ALPHABET) & CONFUSABLE and len(ALPHABET) == 24


@pytest.mark.parametrize(
    ("typed", "code"),
    [
        ("QB-7K4M2", "QB-7K4M2"),
        ("qb-7k4m2", "QB-7K4M2"),
        ("qb 7k4m2", "QB-7K4M2"),
        ("QB7K4M2", "QB-7K4M2"),
        ("7K4M2", "QB-7K4M2"),
        (" 7k4-m2 ", "QB-7K4M2"),
        ("QB–7K4M2", "QB-7K4M2"),  # an en dash from a phone keyboard
        ("QB-٧K٤M٢", "QB-7K4M2"),  # Arabic-Indic digits
        ("QB-7K4M0", None),  # 0 is never in a code
        ("QB-7K4MO", None),
        ("QB-7K4M", None),
        ("QB-7K4M22", None),
        ("", None),
        (None, None),
    ],
)
def test_a_typed_code_is_normalized(typed: str | None, code: str | None) -> None:
    assert normalize(typed) == code
    assert is_code(code) if code else True


def test_the_search_filter() -> None:
    assert "books.code = " in str(code_filter("qb 7k4m2"))
    assert "LIKE" in str(code_filter("7k4"))
    assert code_filter("سلمى") is None and code_filter("7K") is None and code_filter("") is None


def _theme(db: Session) -> Theme:
    theme = Theme(slug="codes-test", title_ar="ت", title_en="t", age_min=3, age_max=7, definition={})
    db.add(theme)
    db.flush()
    return theme


def _book(db: Session, theme: Theme, name: str = "يوسف") -> Book:
    child = Child(first_name=name, gender=Gender.m, birth_year=2020)
    db.add(child)
    db.flush()
    book = Book(child_id=child.id, theme_id=theme.id, theme_version=1, language=Locale.ar, art_style="3d")
    db.add(book)
    db.flush()
    return book


@pytest.fixture
def draws() -> Iterator[list[str]]:
    """Codes the next books draw, in order (then random again)."""
    queue: list[str] = []
    book_codes.set_draw(lambda: queue.pop(0) if queue else generate())
    yield queue
    book_codes.set_draw(None)


def test_every_new_book_gets_its_own_code(db: Session) -> None:
    theme = _theme(db)
    books = [_book(db, theme, f"يوسف {i}") for i in range(5)]  # the same name: told apart by the code
    codes = [b.code for b in books]
    assert all(CODE_RE.fullmatch(c) for c in codes) and len(set(codes)) == 5
    registered = set(db.scalars(select(BookCode.code).where(BookCode.code.in_(codes))))
    assert registered == set(codes)
    book = books[0]
    book.title = "changed"
    db.flush()
    assert book.code == codes[0]  # never changes


def test_a_taken_code_is_drawn_again(db: Session, draws: list[str]) -> None:
    theme = _theme(db)
    first = _book(db, theme)
    draws.extend([first.code, first.code, "QB-AAAAA"])
    second = _book(db, theme)
    assert second.code == "QB-AAAAA"


def test_a_code_is_never_given_twice_even_after_its_book_is_deleted(db: Session, draws: list[str]) -> None:
    theme = _theme(db)
    gone = _book(db, theme)
    code = gone.code
    db.delete(gone)  # «delete all my child's data» removes the books
    db.flush()
    assert db.scalar(select(func.count()).select_from(BookCode).where(BookCode.code == code)) == 1
    draws.extend([code, "QB-CCCCC"])
    assert _book(db, theme).code == "QB-CCCCC"


def test_no_free_code_is_an_error_not_a_duplicate(db: Session, draws: list[str]) -> None:
    theme = _theme(db)
    taken = _book(db, theme).code
    draws.extend(itertools.repeat(taken, book_codes.MAX_ATTEMPTS))
    with pytest.raises(CodeExhausted):
        _book(db, theme)


def _migration() -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob("*_8c3f5a1d7e42_*.py")
    spec = importlib.util.spec_from_file_location("migration_8c3f5a1d7e42", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_gives_every_existing_book_a_code(db: Session) -> None:
    module = _migration()
    assert module.down_revision == "5b7e2c9d4f10"
    assert module.ALPHABET == ALPHABET and module.PREFIX == "QB-"  # the same format as new books
    theme = _theme(db)
    kept = _book(db, theme)
    old = [_book(db, theme, f"قديم {i}") for i in range(12)]
    conn = db.connection()
    conn.execute(text("ALTER TABLE books ALTER COLUMN code DROP NOT NULL"))  # as before the migration
    conn.execute(text("UPDATE books SET code = NULL WHERE id = ANY(:ids)"), {"ids": [b.id for b in old]})
    assert module.backfill(conn) >= 12
    found = conn.execute(
        text("SELECT id, code FROM books WHERE id = ANY(:ids)"), {"ids": [b.id for b in old]}
    )
    rows = {book_id: str(code) for book_id, code in found}
    assert len(rows) == 12 and all(re.fullmatch(CODE_RE, c) for c in rows.values())
    assert len(set(rows.values())) == 12 and kept.code not in rows.values()
    registered = set(
        conn.execute(
            text("SELECT code FROM book_codes WHERE code = ANY(:c)"), {"c": list(rows.values())}
        ).scalars()
    )
    assert registered == set(rows.values())
    assert module.backfill(conn) == 0  # safe to run again
