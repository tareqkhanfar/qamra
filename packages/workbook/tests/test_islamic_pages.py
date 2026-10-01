"""The pages of «قلبي يعرف الله» on the page engine: the 12 samples build in a preview build against a FAKE
corpus, show a
marked placeholder where the Quran file is missing, refuse a print build, the wudu cards shuffle by seed,
and the thin
page types work. No test depends on the real candidates file or on any real verse."""

import asyncio
import datetime as dt
import re
from pathlib import Path
from typing import Any

import pytest
from qamra_workbook import islamic_checks as checks
from qamra_workbook.islamic_sources import (
    SAMPLES,
    Candidate,
    Resolver,
    load,
    parse_quran,
    sha256,
)
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import PageProblems, book_html, build_pages, print_pdf
from qamra_workbook.render.islamic_content import IslamicContext, load_pages, page_spec, parse_page
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.registry import REGISTRY, Assets
from qamra_workbook.render.spec import BookSpec, Child, product_geometry

from qamra_pdf import preflight

DATE = dt.date(2026, 10, 1)
ASSETS = Assets(LibraryStore())


def fake_resolver(*, quran: bool = True) -> Resolver:
    """The real register's ids with FAKE wording: every hadith holds its duas' and the pages' markers (the
    markers are the
    only Arabic, taken from the files), every verse is FAKE-VERSE-n."""
    reg = load()
    raw = checks.load_pages(SAMPLES)
    spans: dict[str, list[str]] = {}
    for src in reg.of_kind("dua"):
        assert src.dua is not None
        spans.setdefault(src.dua.from_, []).append(f"{src.dua.start} فَقَطْ {src.dua.end}")
    for page in raw:
        for req in checks.wording_requests(page):
            if req.span is not None and reg.by_id[req.source].kind == "hadith":
                spans.setdefault(req.source, []).append(f"{req.span.start} فَقَطْ {req.span.end}")
    cands = {}
    for src in reg.of_kind("hadith"):
        text = "نَصٌّ وَهْمِيٌّ لِلِاخْتِبَارِ، " + " ، ".join(spans.get(src.id, [])) + " ، تَمَّ"
        assert src.hadith is not None
        cands[src.id] = Candidate(
            src.id, "hadith", text, sha256(text), "matched", "fake", "fake", src.hadith.number
        )
    lines = []
    for src in reg.of_kind("quran"):
        assert src.quran is not None
        lines += [
            f"{src.quran.surah}|{n}|FAKE-VERSE-{src.quran.surah}-{n}"
            for n in range(src.quran.from_, src.quran.to + 1)
        ]
    file = parse_quran("# FAKE\n" + "\n".join(sorted(set(lines))) + "\n") if quran else None
    return Resolver(reg, file, cands)


def build(
    pages: list[Any],
    resolver: Resolver,
    *,
    mode: str = "preview",
    gender: str = "f",
    size: str = "21x28",
    tmp: Path | None = None,
) -> list[Any]:
    context = IslamicContext(resolver, Kit(), mode, DATE)  # type: ignore[arg-type]
    book = BookSpec(
        product="islamic",
        title_ar="قلبي يعرف الله",
        child=Child("ليان" if gender == "f" else "يوسف", gender),  # type: ignore[arg-type]
        pages=tuple(page_spec(p, i, context) for i, p in enumerate(pages, start=1)),
        date=DATE,
        geometry=product_geometry("family", size),
    )
    return build_pages(book, ASSETS)


@pytest.fixture(scope="module")
def samples() -> list[Any]:
    return load_pages(SAMPLES)


def test_all_twelve_samples_build_and_pass_the_checks_in_preview_mode(samples: list[Any]) -> None:
    res = fake_resolver()
    raw = checks.load_pages(SAMPLES)
    assert checks.errors(checks.check_pages(raw, res, checks.PageRules.load())) == []
    built = build(samples, res)
    assert [p.spec.type for p in built] == [
        "prophet-story", "wudu-steps", "dhikr-situation",
        "what-would-you-do", "what-do-i-do-if", "islamic-coloring",
        "blessings-hunt", "islamic-unit-review", "parent-guide",
        "muslim-passport", "muslim-certificate", "surah-page",
    ]  # fmt: skip
    assert all(not p.built.problems for p in built)


@pytest.mark.parametrize("size", ["21x28", "a4"])
@pytest.mark.parametrize("gender", ["f", "m"])
def test_the_samples_follow_the_childs_gender_and_size(samples: list[Any], gender: str, size: str) -> None:
    built = build(samples, fake_resolver(), gender=gender, size=size)
    by_id = {p.spec.id: p for p in built}
    assert by_id["s02-wudu"].instruction == (
        "رَتِّبِي الْخُطُوَاتِ مِنْ ١ إِلَى ٨" if gender == "f" else "رَتِّبِ الْخُطُوَاتِ مِنْ ١ إِلَى ٨"
    )
    assert (
        "الْمُسْلِمَةِ" in by_id["s10-passport"].title if gender == "f" else "الْمُسْلِمِ" in by_id["s10-passport"].title
    )
    assert ("مُسْلِمَةٌ" in by_id["s11-certificate"].built.data["statement"]) == (gender == "f")


def test_the_placeholder_shows_when_there_is_no_quran_file(samples: list[Any]) -> None:
    built = {p.spec.id: p for p in build(samples, fake_resolver(quran=False))}
    verse = built["s12-surah-ikhlas"].built.data["verse"]
    assert verse["placeholder"] and verse["text"] is None and "طنزيل" in verse["notice"]
    html = book_html(
        BookSpec("islamic", "ت", Child("ليان", "f"), (), DATE, geometry=product_geometry("family")),
        list(built.values())[11:],
        ASSETS,
    )
    assert "طنزيل" in html and "FAKE-VERSE" not in html
    with_file = {p.spec.id: p for p in build(samples, fake_resolver())}
    assert not with_file["s12-surah-ikhlas"].built.data["verse"]["placeholder"]
    assert with_file["s12-surah-ikhlas"].built.data["verse"]["lines"][0]["text"].startswith("FAKE-VERSE-112")


def test_a_print_build_refuses_a_placeholder_and_unapproved_sources(samples: list[Any]) -> None:
    with pytest.raises(PageProblems, match=r"print build|scholar_approved"):
        build(samples[11:12], fake_resolver(quran=False), mode="print")
    with pytest.raises(PageProblems, match="scholar_approved"):
        build(samples[11:12], fake_resolver(), mode="print")  # the text is there but nothing is approved


def test_candidate_wording_is_marked_in_a_preview_build(samples: list[Any]) -> None:
    built = {p.spec.id: p for p in build(samples, fake_resolver())}
    dhikr = built["s03-dhikr-eating"].built.data["dhikr"]
    assert dhikr["text"] and "مرشَّح" in dhikr["tag"]
    options = built["s08-unit-review"].built.data["choose"]["choices"]
    assert len(options) == 3 and all(o["tag"] for o in options) and sum(o["ok"] for o in options) == 1


def test_inline_tokens_resolve_from_the_register_with_their_digits_intact(samples: list[Any]) -> None:
    built = {p.spec.id: p for p in build(samples, fake_resolver())}
    habit = str(built["s09-parent-guide"].built.data["sections"][4]["text"])
    assert "{src:" not in habit and 'class="cand"' in habit
    third = str(built["s08-unit-review"].built.data["rows"][2]["text"])
    assert "{src:" not in third


def test_wudu_cards_shuffle_by_seed_and_the_key_lists_the_right_order(samples: list[Any]) -> None:
    first = build(samples[1:2], fake_resolver())[0]
    again = build(samples[1:2], fake_resolver())[0]
    texts = [c["text"] for c in first.built.data["cards"]]
    assert texts == [c["text"] for c in again.built.data["cards"]]  # deterministic
    assert len(texts) == 8 and texts != sorted(
        texts, key=lambda t: first.built.answer.index(next(a for a in first.built.answer if t in a))
    )
    assert first.built.answer is not None and first.built.answer[0].startswith("١) ")
    # type: ignore[union-attr]
    assert [re.match(r"(.)\)", a).group(1) for a in first.built.answer] == list("١٢٣٤٥٦٧٨")


def test_no_prophet_page_scene_draws_a_person(samples: list[Any]) -> None:
    story = samples[0]
    broken = story.model_copy(update={"scenes": [story.scenes[0].model_copy(update={"art": "family-meal"})]})
    with pytest.raises(PageProblems, match="draws people"):
        build([broken], fake_resolver())


def test_the_coloring_page_carries_no_source_and_the_wudu_art_is_never_a_person(samples: list[Any]) -> None:
    coloring = build(samples[5:6], fake_resolver())[0]
    assert "refs" not in coloring.built.data and "verse" not in coloring.built.data
    from qamra_workbook.pictures.islamic import SCENES, WUDU_ICONS

    assert not SCENES["blessings-garden"].figures
    assert set(WUDU_ICONS) == {"speech-bubble", "hands", "mouth", "nose", "face", "arms", "head", "feet"}


def test_the_series_page_types_are_registered_with_their_islamic_templates() -> None:
    names = {
        "prophet-story", "wudu-steps", "dhikr-situation",
        "what-would-you-do", "what-do-i-do-if", "blessings-hunt",
        "islamic-coloring", "islamic-unit-review", "parent-guide",
        "muslim-passport", "muslim-certificate", "surah-page",
        "prayer-steps", "my-day-with-allah", "pillar-card", "true-false", "unit-closing", "final-assessment",
    }  # fmt: skip
    from qamra_workbook.render.engine import TEMPLATES

    for name in names:
        template = REGISTRY[name].template
        assert (TEMPLATES / template).is_file(), template
        assert template.split("/")[1].startswith("islamic-")


THIN: list[dict[str, Any]] = [
    {
        "id": "t1",
        "type": "prayer-steps",
        "unit": "u-prayer",
        "title": "أُصَلِّي",
        "instruction": "رَتِّبِ الْخُطُوَاتِ",
        "steps": [{"n": 1, "t": "أَقِفُ"}, {"n": 2, "t": "أَرْكَعُ"}, {"n": 3, "t": "أَسْجُدُ"}],
    },
    {
        "id": "t2",
        "type": "true-false",
        "unit": "u-allah",
        "title": "صَحٌّ أَمْ خَطَأٌ؟",
        "instruction": "حَوِّطْ الْجَوَابَ",
        "statements": [{"t": "جُمْلَةٌ أُولَى", "ok": True}, {"t": "جُمْلَةٌ ثَانِيَةٌ", "ok": False}],
    },
    {
        "id": "t3",
        "type": "pillar-card",
        "unit": "u-house",
        "title": "رُكْنٌ",
        "pillar": "الصَّلَاةُ",
        "idea": {"text": "فِكْرَةٌ فِي سَطْرَيْنِ", "sources": ["q-1-2"], "ai_drafted": True},
        "question": {"text": "سُؤَالٌ؟", "choices": [{"t": "نَعَمْ", "ok": True}, {"t": "لَا"}]},
    },
    {
        "id": "t4",
        "type": "my-day-with-allah",
        "unit": "u-myday1",
        "title": "يَوْمِي مَعَ اللهِ",
        "moments": [
            {"when": "صَبَاحًا", "t": "أَسْتَيْقِظُ", "picture": "sun"},
            {"when": "مَسَاءً", "t": "أَنَامُ", "picture": "bed"},
        ],
    },
    {
        "id": "t5",
        "type": "unit-closing",
        "unit": "u-blessings",
        "title": "خَاتِمَةُ الْوَحْدَةِ",
        "learned": ["تَعَلَّمْتُ شَيْئًا"],
        "apply": "سَأُطَبِّقُ",
        "dhikr": {"source": "d-eat-start"},
        "challenge": "تَحَدٍّ مَعَ أُمِّي",
    },
    {
        "id": "t6",
        "type": "final-assessment",
        "unit": "u-manners1",
        "title": "لُعْبَةٌ لَا امْتِحَانٌ",
        "instruction": "الْعَبْ",
        "skills": [{"skill": "الصِّدْقُ", "t": "يَقُولُ الْحَقَّ"}],
    },
]


def test_the_thin_page_types_build_and_render(tmp_path: Path) -> None:
    pages = [parse_page(p) for p in THIN]
    res = fake_resolver()
    assert checks.errors(checks.check_pages(THIN, res, checks.PageRules.load())) == []
    built = build(pages, res)
    assert [p.spec.type for p in built] == [
        "prayer-steps",
        "true-false",
        "pillar-card",
        "my-day-with-allah",
        "unit-closing",
        "final-assessment",
    ]
    context = IslamicContext(res, Kit(), "preview", DATE)  # type: ignore[arg-type]
    book = BookSpec(
        "islamic",
        "ت",
        Child("ليان", "f"),
        tuple(page_spec(p, i, context) for i, p in enumerate(pages, 1)),
        DATE,
        geometry=product_geometry("family"),
    )
    pdf = asyncio.run(
        print_pdf(book_html(book, built, ASSETS), tmp_path / "t.html", tmp_path / "t.pdf", book.geometry)
    )
    assert pdf.exists()


def test_the_samples_render_to_a_print_pdf_that_passes_preflight(samples: list[Any], tmp_path: Path) -> None:
    res = fake_resolver()
    context = IslamicContext(res, Kit(), "preview", DATE)  # type: ignore[arg-type]
    g = product_geometry("family")
    book = BookSpec(
        "islamic",
        "قلبي يعرف الله",
        Child("ليان", "f"),
        tuple(page_spec(p, i, context) for i, p in enumerate(samples, 1)),
        DATE,
        geometry=g,
    )
    built = build_pages(book, ASSETS)
    pdf = asyncio.run(print_pdf(book_html(book, built, ASSETS), tmp_path / "s.html", tmp_path / "s.pdf", g))
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed, [c for c in report.to_dict()["checks"] if not c["ok"]]
    fonts = next(c for c in report.to_dict()["checks"] if c["name"] == "fonts_embedded")
    assert fonts["ok"]
