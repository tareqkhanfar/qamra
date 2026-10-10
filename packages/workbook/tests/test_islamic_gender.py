# ruff: noqa: E501  (Arabic fixtures are one line each)
"""«قلبي يعرف الله» for a boy and for a girl, as the gender audit of 2026-10-09 dumped it: every volume (V1–V5, R)
printed both ways (interior, answer key, cover, sticker sheet) and read back as text. No `{…}` or `{src:…}` is left
in any printed string, both copies have the same pages, the lines the audit fixed print in the child's gender
(the girl's copy was approved by the owner; the boy's had never been read), and the answer keys speak Arabic.
FAKE corpus (`fake_resolver`); the verses and hadith are not part of these checks."""

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from qamra_workbook import islamic
from qamra_workbook.pictures.islamic_icons import UNIT_GLYPHS
from qamra_workbook.render import islamic_volume as iv
from qamra_workbook.render.engine import answer_key_html, book_html, build_pages
from qamra_workbook.render.islamic_content import IslamicContext, parse_page
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.pages.islamic_play import GLYPH_WORDS, word_of
from qamra_workbook.render.spec import Child
from qamra_workbook.render.stickers import sheet_book
from test_islamic_pages import ASSETS, DATE, fake_resolver
from test_islamic_volume import book_of

VOLUMES = ("V1", "V2", "V3", "V4", "V5", "R")
NAMES = {"m": "يوسف", "f": "ليان"}
CONTENT = Path(__file__).resolve().parents[3] / "content/islamic"
VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")


class _Text(HTMLParser):
    """The printed strings of a rendered book, page by page (`<section class="page" data-page>`): CSS, scripts
    and SVG drawing data are not printed; an SVG `<text>` is."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: list[tuple[str, list[str]]] = [("", [])]
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "section" and "page" in (a.get("class") or "").split() and a.get("data-page"):
            self.pages.append((a["data-page"] or "", []))
        if tag not in ("br", "img", "meta", "link", "input", "hr"):
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass

    def handle_endtag(self, tag: str) -> None:
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag) :]

    def handle_data(self, data: str) -> None:
        if any(t in ("style", "script", "title") for t in self.stack):
            return
        if "svg" in self.stack and "text" not in self.stack:
            return  # SVG character data outside <text> is never drawn
        if data.strip():
            self.pages[-1][1].append(" ".join(data.split()))


def printed(html: str) -> list[tuple[str, str]]:
    """(page id, its printed text) for every page of a rendered book."""
    parser = _Text()
    parser.feed(html)
    return [(pid, " ".join(lines)) for pid, lines in parser.pages if pid or lines]


@pytest.fixture(scope="module")
def books() -> dict[tuple[str, str], dict[str, Any]]:
    """Every volume for a boy and for a girl: the built interior and the four rendered documents."""
    plan, resolver = islamic.load(), fake_resolver()
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for vid in VOLUMES:
        content = iv.check_volume(plan, vid, resolver, build=False)
        assert content.errors == [], (vid, content.errors[:3])
        for gender, name in NAMES.items():
            context = IslamicContext(resolver, Kit(), "preview", DATE)
            book = iv.volume_book(plan, content, context, Child(name, gender))  # type: ignore[arg-type]
            pages = build_pages(book, ASSETS)
            cover = iv.cover_book(plan, vid, context, book, pages=len(content.slots))
            sheet = sheet_book(book)
            out[vid, gender] = {
                "keys": {p.id: str(p.params.get("key", "")) for p in book.pages},
                "pages": pages,
                "interior": book_html(book, pages, ASSETS),
                "answer-key": answer_key_html(book, pages, ASSETS),
                "cover": book_html(cover, build_pages(cover, ASSETS), ASSETS),
                "stickers": book_html(sheet, build_pages(sheet, ASSETS), ASSETS),
            }
    return out


def page_text(books: dict[tuple[str, str], dict[str, Any]], vid: str, gender: str, key: str) -> str:
    book = books[vid, gender]
    pid = next(pid for pid, k in book["keys"].items() if k == key)
    return next(text for page, text in printed(book["interior"]) if page == pid)


# ---- the whole series, both ways ---------------------------------------------------------------------------


@pytest.mark.parametrize("vid", VOLUMES)
def test_every_printed_string_is_resolved_for_a_boy_and_for_a_girl(
    books: dict[tuple[str, str], dict[str, Any]], vid: str
) -> None:
    for gender, name in NAMES.items():
        book = books[vid, gender]
        for part in ("interior", "answer-key", "cover", "stickers"):
            for pid, text in printed(book[part]):
                assert not re.search(r"[{}]|src:", text), (vid, gender, part, pid, text[:200])
        assert name in " ".join(text for _, text in printed(book["interior"]))
    boy, girl = (printed(books[vid, g]["interior"]) for g in "mf")
    assert [pid for pid, _ in boy] == [pid for pid, _ in girl]
    assert sum(b != g for (_, b), (_, g) in zip(boy, girl, strict=True)) > len(boy) // 2  # the copies differ


@pytest.mark.parametrize("vid", VOLUMES)
def test_the_answer_keys_name_every_picture_in_arabic_and_resolve_every_source(
    books: dict[tuple[str, str], dict[str, Any]], vid: str
) -> None:
    """No icon id («prayer-mat») and no `{src:…}` token in an answer; FAKE verses are upper case."""
    for gender in NAMES:
        for page in books[vid, gender]["pages"]:
            for line in page.built.answer or []:
                assert not re.search(r"[a-z{}]", str(line)), (vid, gender, page.spec.id, line)


# ---- the lines the audit fixed ------------------------------------------------------------------------------


@pytest.mark.parametrize("vid", VOLUMES)
def test_this_is_me_agrees_with_the_child(books: dict[tuple[str, str], dict[str, Any]], vid: str) -> None:
    key = next(
        k
        for k in books[vid, "f"]["keys"].values()
        if k.startswith(("front/", "end/")) and "هَذِهِ أَنَا" in page_text(books, vid, "f", k)
    )
    assert "هَذِهِ أَنَا" not in page_text(books, vid, "m", key)
    assert "هَذَا أَنَا" in page_text(books, vid, "m", key)
    assert "هَذَا أَنَا" not in page_text(books, vid, "f", key)


@pytest.mark.parametrize(
    ("vid", "key", "boy", "girl"),
    [
        # the lesson titles the reader says of themself (the unit opener lists them; the lesson pages carry them)
        ("V1", "u-manners1/opener", "أَقُولُ: شُكْرًا وَآسِفٌ", "أَقُولُ: شُكْرًا وَآسِفَةٌ"),
        ("V5", "u-manners2/opener", "أَمِينٌ عَلَى مَا عِنْدِي", "أَمِينَةٌ عَلَى مَا عِنْدِي"),
        ("V5", "u-manners2/l2-3", "أَمِينٌ عَلَى مَا عِنْدِي", "أَمِينَةٌ عَلَى مَا عِنْدِي"),
        ("V5", "u-whatif2/opener", "لَوْ ظَلَمْتُ صَدِيقِي", "لَوْ ظَلَمْتُ صَدِيقَتِي"),
        ("V5", "u-whatif2/l4-3", "لَوْ ظَلَمْتُ صَدِيقِي", "لَوْ ظَلَمْتُ صَدِيقَتِي"),
        # a choice about the girl's friends («صَدِيقَاتِكِ»): «يَنْظُرْنَ»
        ("V5", "u-halal/l2-2", "حِينَ لَا يَنْظُرُونَ", "حِينَ لَا يَنْظُرْنَ"),
        # feedback to the reader: the reader's mother, not the speaker's
        ("V1", "u-blessings/l3-3", "وَشُكْرُ أُمِّكَ", "وَشُكْرُ أُمِّكِ"),
        # the parents' question to this child («سؤال نسأله له»)
        ("V1", "u-follow/parent", "ماذا فعلتَ اليوم", "ماذا فعلتِ اليوم"),
        ("V1", "u-manners1/parent", "متى قلتَ الصدق", "متى قلتِ الصدق"),
        ("V2", "u-prayer/parent", "ماذا تقول في السجود؟", "ماذا تقولين في السجود؟"),
        ("V3", "u-iman2/parent", "ولم تستسلم؟", "ولم تستسلمي؟"),
        ("V4", "u-musa/parent", "يجعلك تطمئنّ؟", "يجعلك تطمئنّين؟"),
        ("V5", "u-myday2/parent", "مع الله تحبها أكثر", "مع الله تحبينها أكثر"),
        ("R", "u-ram4/parent", "بماذا تدعو الله؟", "بماذا تدعين الله؟"),
    ],
)
def test_the_lines_the_audit_fixed_print_in_the_childs_gender(
    books: dict[tuple[str, str], dict[str, Any]], vid: str, key: str, boy: str, girl: str
) -> None:
    assert boy in page_text(books, vid, "m", key) and girl not in page_text(books, vid, "m", key)
    assert girl in page_text(books, vid, "f", key) and boy not in page_text(books, vid, "f", key)


def test_a_boys_imperative_keeps_its_sukun_before_a_word_without_wasl(
    books: dict[tuple[str, str], dict[str, Any]],
) -> None:
    text = page_text(books, "V1", "m", "u-follow/l1-2")
    assert "اخْتَرْ مَا يُشْبِهُ" in text and "اخْتَرِ مَا" not in text


def test_the_salawat_page_frames_the_verse_as_allahs_command_not_as_the_childs_words(
    books: dict[tuple[str, str], dict[str, Any]],
) -> None:
    for gender in NAMES:
        text = page_text(books, "V2", gender, "u-adhkar2/l3-1")
        assert "قَالَ اللهُ تَعَالَى" in text and "أَقُولُ" not in text
        assert "قُلْتُ: صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ" in text
    assert "أَقُولُ" in page_text(books, "V2", "f", "u-adhkar2/l2-1")  # a dhikr the child says keeps «أَقُولُ»


def test_every_variant_in_the_content_has_two_different_sides() -> None:
    files = [*CONTENT.glob("pages/*.yaml"), *CONTENT.glob("volumes/*.yaml")]
    same = [
        (f.name, m.group(0))
        for f in files
        for m in VARIANT.finditer(f.read_text(encoding="utf-8"))
        if m.group(1).strip() == m.group(2).strip()
    ]
    assert same == []


# ---- the answer keys ----------------------------------------------------------------------------------------


def test_every_series_icon_has_its_word_for_the_answer_key() -> None:
    assert set(UNIT_GLYPHS) <= set(GLYPH_WORDS)
    assert word_of("isl:prayer-mat") == "سَجَّادَةُ الصَّلَاةِ" and word_of("isl:cube") == "الْكَعْبَةُ"


def test_an_answer_key_repeats_the_question_and_prints_a_sources_wording() -> None:
    resolver = fake_resolver()
    pages = [
        parse_page({"id": "o", "type": "prayer-steps", "title": "أُرَتِّبُ", "steps": [{"n": 1, "t": "أُكَبِّرُ."}, {"n": 2, "t": "أَرْكَعُ وَأَقُولُ: {src:d-ruku}"}]}),
        parse_page({"id": "p", "type": "pillar-card", "title": "رُكْنٌ", "pillar": "الصَّلَاةُ", "idea": {"text": "نُصَلِّي."}, "question": {"text": "كَمْ صَلَاةً نُصَلِّي؟", "choices": [{"t": "خَمْسًا", "ok": True}, {"t": "وَاحِدَةً"}]}}),
    ]  # fmt: skip
    for gender in NAMES:
        order, pillar = build_pages(book_of(pages, resolver, gender=gender), ASSETS)
        assert order.built.answer is not None and "{src:" not in order.built.answer[1]
        assert (
            order.built.answer[1].startswith("٢) أَرْكَعُ وَأَقُولُ: ") and order.built.answer[1] != "٢) أَرْكَعُ وَأَقُولُ: "
        )
        assert pillar.built.answer == ["كَمْ صَلَاةً نُصَلِّي؟", "الجواب: خَمْسًا"]
