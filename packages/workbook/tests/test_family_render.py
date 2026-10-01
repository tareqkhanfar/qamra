"""«مغامراتي مع عائلتي» on the page engine (Addendum 7): the family product, personalization and its page
types, the parent box, the inserts."""

import asyncio
import dataclasses
import datetime as dt
import re
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from qamra_workbook.family import Activity, FamilyPlan, Levels, Page, Proposal, Section, book_pages
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import PageProblems, book_html, build_pages, print_pdf
from qamra_workbook.render.pages.inserts import FOR_PLAY, REAL_MONEY
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import SPECS, FamilySamples, book_from, book_problems, inserts_from, load
from qamra_workbook.render.sections import section_style, tab_top
from qamra_workbook.render.spec import (
    ActivityTags,
    BookSpec,
    Child,
    Family,
    Member,
    PageSpec,
    from_family,
    product_geometry,
)

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "content" / "family-book" / "plan.yaml"
ASSETS = Assets(LibraryStore())
MM = 72 / 25.4
TOGETHER = ActivityTags("home", together=True, minutes=10, challenge=True)
KHATIB = Family(
    "الخطيب",
    (Member("ماما", scarf=True), Member("بابا"), Member("أخي", "كرم"), Member("ستّي", scarf=True)),
    "رام الله",
)
LONG_SIX = Family(
    "أبو الهيجاء الكيلاني",
    (
        Member("ماما", "نور الهدى", scarf=True),
        Member("بابا", "عبد الرحمن"),
        Member("أخي", "محمد الأمين"),
        Member("أختي", "سلسبيل"),
        Member("ستّي", "أم خليل", scarf=True),
        Member("سيدي", "أبو خليل"),
    ),
    "بيت ساحور",
)
GRANDMOTHER_ONLY = Family("الكيلاني", (Member("ستّي"),), "الخليل")
PARENT = (
    "تجوّلوا مع {child} في المطبخ، وسمّوا مع {adult} كل شيء دائري.",
    "اسألوا {member}: أيّها أكبر؟ أيّها أصغر؟ كم دائرة وجدنا؟",
    "امدحوا الملاحظة: «عيناك عينا {محقّق صغير/محقّقة صغيرة}!»",
)


def page(n: int, kind: str, section: str, **params: Any) -> PageSpec:
    return PageSpec(
        id=f"family-p{n}",
        type=kind,
        number=n,
        section=section,
        title="مغامرة {child}",
        instruction="{ابحث/ابحثي} عن أشياء دائرية في المطبخ",
        params=params,
        parent=PARENT if kind not in ("certificate-family", "section-opener") else (),
        activity=TOGETHER if kind not in ("certificate-family", "section-opener", "passport") else None,
    )


def book(*pages: PageSpec, family: Family = KHATIB, child: Child | None = None) -> BookSpec:
    return BookSpec(
        "family",
        "مغامراتي مع عائلتي",
        child or Child("ليان", "f"),
        pages,
        dt.date(2026, 9, 28),
        geometry=product_geometry("family"),
        family=family,
    )


def render(b: BookSpec, tmp: Path) -> Path:
    pages = build_pages(b, ASSETS)
    return asyncio.run(print_pdf(book_html(b, pages, ASSETS), tmp / "b.html", tmp / "b.pdf", b.geometry))


def test_a_family_page_prints_on_21_by_28_cm_with_bleed(tmp_path: Path) -> None:
    pdf = render(book(page(8, "scavenger-hunt", "home", examples=["plate", "orange", "clock"])), tmp_path)
    reader = PdfReader(pdf)
    assert len(reader.pages) == 1
    p = reader.pages[0]
    assert float(p.mediabox.width) / MM == pytest.approx(216, abs=0.01)
    assert float(p.mediabox.height) / MM == pytest.approx(286, abs=0.01)
    assert float(p.trimbox.left) / MM == pytest.approx(3, abs=0.01)
    assert float(p.trimbox.width) / MM == pytest.approx(210, abs=0.01)
    assert float(p.trimbox.height) / MM == pytest.approx(280, abs=0.01)
    report = preflight(pdf, width_mm=216, height_mm=286, bleed_mm=3, safe_mm=12)
    assert report.passed and all(c.ok for c in report.checks), report.to_dict()


def test_family_placeholders_resolve_for_the_page() -> None:
    b = book(page(8, "scavenger-hunt", "home"))
    text = "{child} مع {adult} و{member} من عائلة {family_name} في {city}: {ابحث/ابحثي}"
    chosen = dataclasses.replace(b.pages[0], params={"adult": "بابا", "member": "كرم"})
    assert b.personalize(text, chosen) == "ليان مع بابا وكرم من عائلة الخطيب في رام الله: ابحثي"
    # without a choice, the missions go round the family by page number (never a fixed mother and father)
    grown_ups = {b.personalize("{adult}", dataclasses.replace(chosen, number=n, params={})) for n in range(6)}
    assert grown_ups == {"ماما", "بابا", "ستّي"}
    lone = book(page(8, "scavenger-hunt", "home"), family=Family("الكيلاني", (Member("أخي", "كرم"),)))
    assert lone.personalize("مع {adult}", lone.pages[0]) == "مع أحد الكبار"
    rendered = build_pages(book(page(8, "scavenger-hunt", "home")), ASSETS)[0]
    assert rendered.title == "مغامرة ليان" and rendered.instruction == "ابحثي عن أشياء دائرية في المطبخ"
    assert "ليان" in rendered.parent[0] and "محقّقة صغيرة" in rendered.parent[2]
    assert not any("{" in line for line in rendered.parent)


def test_a_page_never_prints_an_unresolved_placeholder() -> None:
    journeyish = dataclasses.replace(book(page(8, "scavenger-hunt", "home")), family=None)
    with pytest.raises(PageProblems, match=r"unresolved \['\{adult\}'\]"):
        build_pages(journeyish, ASSETS)


def test_a_family_lists_one_to_six_members() -> None:
    with pytest.raises(ValueError, match="1–6 members"):
        Family("الخطيب", ())
    with pytest.raises(ValueError, match="1–6 members"):
        Family("الخطيب", tuple(Member("أخي", f"كرم {i}") for i in range(7)))
    assert [m.drawn_as for m in KHATIB.members] == ["woman", "man", "boy", "grandma"]
    assert [m.label for m in KHATIB.members] == ["ماما", "بابا", "كرم", "ستّي"]


@pytest.mark.parametrize("family", [GRANDMOTHER_ONLY, LONG_SIX], ids=["one member", "six members"])
def test_long_names_and_big_families_fit_the_parent_box_and_the_certificate(
    tmp_path: Path, family: Family
) -> None:
    """The engine shrinks personalized text to fit and refuses to print anything that still overflows, so a
    clean render is the proof; the grown-up line, the family line and every name tag are on the page."""
    child = Child("سلسبيل نور الهدى", "f")
    pages = (
        page(3, "passport", "front"),
        page(6, "section-opener", "home", badge="{مستكشف/مستكشفة} البيت"),
        page(7, "section-opener", "home", badge="{مستكشف/مستكشفة} البيت"),
        page(8, "scavenger-hunt", "home"),
        page(15, "memory-page", "home"),
        page(112, "certificate-family", "back"),
    )
    b = book(*pages, family=family, child=child)
    pdf = render(b, tmp_path)
    assert len(PdfReader(pdf).pages) == len(pages)
    html = (tmp_path / "b.html").read_text(encoding="utf-8")
    assert f"عائِلَةُ {family.name}" in html
    assert all(m.label in html for m in family.members)
    assert html.count('class="op-tag') == len(family.members) + 1  # the child and every member on the spread
    assert html.count('<aside class="parent-box') == 3  # passport, hunt, memory page; never the certificate


def test_a_name_too_long_to_fit_stops_the_render(tmp_path: Path) -> None:
    b = book(page(112, "certificate-family", "back"), child=Child("عبد الرحمن " * 9, "m"))
    with pytest.raises(PageProblems, match="does not fit"):
        render(b, tmp_path)


def test_the_parent_box_is_titled_for_the_activity() -> None:
    together = build_pages(book(page(8, "scavenger-hunt", "home")), ASSETS)
    alone = [
        dataclasses.replace(p, activity=ActivityTags("home"))
        for p in book(page(8, "scavenger-hunt", "home")).pages
    ]
    b = book(*alone)
    html_together = book_html(book(page(8, "scavenger-hunt", "home")), together, ASSETS)
    html_alone = book_html(b, build_pages(b, ASSETS), ASSETS)
    assert "هيا نفعلها معًا!" in html_together and "للأهل" in html_together
    assert "هيا نفعلها معًا!" not in html_alone and "للأهل" in html_alone
    for icon in ("t-home", "t-fam", "t-time", "t-level"):
        assert f"tag {icon}" in html_together
    assert "١٠ دقائق" in html_together
    too_long = dataclasses.replace(b.pages[0], parent=("١", "٢", "٣", "٤"))
    with pytest.raises(PageProblems, match="parent box has 4 lines"):
        build_pages(book(too_long), ASSETS)


def test_play_money_is_for_play_only(tmp_path: Path) -> None:
    money = page(0, "play-money", "shop", notes=[5, 10, 20], coins=[1, 2, 2])
    money = dataclasses.replace(
        money, id="family-insert-play-money", title="نقود قمرة للّعب", parent=(), activity=None
    )
    b = book(money)
    built = build_pages(b, ASSETS)[0].built
    assert len(built.data["notes"]) == 3 and len(built.data["coins"]) == 3
    assert all(item["play"] == FOR_PLAY for item in [*built.data["notes"], *built.data["coins"]])
    html = book_html(b, build_pages(b, ASSETS), ASSETS)
    assert html.count(f">{FOR_PLAY}<") >= 6  # on every note and every coin
    assert f"{FOR_PLAY} — نُقودُ قَمْرَةَ" in html
    printed = re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", "", html, flags=re.S))
    assert not REAL_MONEY.search(printed)
    shekels = dataclasses.replace(money, title="نقود بالشيكل")
    with pytest.raises(PageProblems, match="real currency"):
        build_pages(book(shekels), ASSETS)
    render(b, tmp_path)


def test_a_recipe_carries_its_safety_box() -> None:
    steps = [
        {"picture": "wash", "text": "نغسل أيدينا"},
        {"picture": "roll", "text": "نصنع كرات"},
        {"picture": "dip", "text": "نغمّسها"},
    ]
    safe = ["نغسل أيدينا قبل أن نبدأ", "السكين والنار للكبار فقط", "اسألوا عن الحساسية (الحليب)"]

    def recipe(safety: list[str], ingredients: list[dict[str, Any]]) -> PageSpec:
        return page(
            30,
            "recipe-steps",
            "chef",
            steps=steps,
            shown=[2, 3, 1],
            ingredients=ingredients,
            safety=[{"text": t} for t in safety],
        )

    ok = build_pages(book(recipe(safe, [{"picture": "labneh", "name": "لبنة", "count": 2}])), ASSETS)[0]
    assert ok.built.answer == ["الترتيب: ١ نغسل أيدينا، ٢ نصنع كرات، ٣ نغمّسها"]
    with pytest.raises(PageProblems, match="ask about allergies"):
        build_pages(book(recipe(safe[:2], [{"picture": "labneh", "name": "لبنة"}])), ASSETS)
    with pytest.raises(PageProblems, match="no nuts or raw eggs"):
        build_pages(book(recipe(safe, [{"picture": "labneh", "name": "جوز"}])), ASSETS)


def test_section_names_are_personalized() -> None:
    specs = (page(60, "memory-page", "responsible"), page(30, "memory-page", "chef"))
    girl = build_pages(book(*specs), ASSETS)
    assert [p.section_name for p in girl] == ["أنا مسؤولة", "الشيف الصغيرة"]
    assert build_pages(book(specs[0], child=Child("كرم", "m")), ASSETS)[0].section_name == "أنا مسؤول"
    html = book_html(book(*specs), girl, ASSETS)
    assert "أنا مسؤولة" in html and "{أنا مسؤول/" not in html


FAMILY_ORDER = ["home", "market", "chef", "nature", "day", "responsible", "feelings", "talk", "jobs", "shop"]
FAMILY_ORDER += ["games", "act"]


def test_the_family_book_has_its_own_section_styles() -> None:
    assert section_style("games").name_ar == "ألعاب التفكير"  # the journey's, as before
    games = section_style("games", "family")
    assert games.name_ar == "ليلة الألعاب العائلية" and games.slots == 14
    styles = [section_style(s, "family") for s in ["front", *FAMILY_ORDER, "back"]]
    assert [s.slot for s in styles] == list(range(14))  # the tabs step down in the book's order
    assert len({s.color for s in styles}) == len(styles) and len({s.pattern for s in styles}) == len(styles)
    tops = [tab_top(s, 280, 3) for s in styles]
    assert tops == sorted(tops) and tops[-1] + 26 <= 3 + 280 - 18 + 0.01  # a thumb index inside the trim
    if PLAN.exists():
        from qamra_workbook.family import load as load_plan

        assert [s.id for s in load_plan(PLAN).sections] == FAMILY_ORDER


def test_the_opening_spread_shares_one_landscape() -> None:
    first, second = build_pages(
        book(
            page(6, "section-opener", "home", badge="{مستكشف/مستكشفة} البيت", adventure=1),
            page(7, "section-opener", "home", badge="{مستكشف/مستكشفة} البيت", adventure=1),
        ),
        ASSETS,
    )
    assert (first.side, second.side) == ("right", "left")  # the spread opens on the right-hand page
    assert first.built.data["first"] and not second.built.data["first"]
    same = [re.sub(r"sky-family-p\d+", "sky", str(p.built.data["art"])) for p in (first, second)]
    assert same[0] == same[1]
    assert first.built.data["shift"] == -210 and second.built.data["shift"] == 0
    assert second.built.data["badge_label"] == "مستكشفة البيت"
    assert [t["label"] for t in second.built.data["tags"]] == ["كرم", "ماما", "ليان", "بابا", "ستّي"]


def test_plan_pages_become_engine_pages() -> None:
    hunt = Page(type="scavenger-hunt", title="صيد الدوائر", instruction="ابحث", parent=["مع {adult}"])
    activity = Activity(
        id="home-circles",
        section="home",
        title="صيد الدوائر",
        goal="الملاحظة",
        skills=["observation", "counting"],
        child_part="يبحث",
        together=True,
        where="home",
        minutes=10,
        levels=Levels(simple="٣", challenge="٥"),
        pages=[hunt],
    )
    plan = FamilyPlan(
        title_ar="مغامراتي مع عائلتي", title_en="My Adventures",
        proposal=Proposal(concept="", size="", paper="", binding=""),
        front=[Page(type="passport", title="جواز", instruction="الصق")],
        sections=[Section(id="home", title_ar="بيتي مدرسة", icon="🏠", hook="حكاية", badge="مستكشف البيت")],
        activities=[activity], back=[], inserts=[], samples=[],
    )  # fmt: skip
    specs = [from_family(p, plan) for p in book_pages(plan)]
    assert [(s.number, s.type) for s in specs] == [
        (1, "passport"), (2, "section-opener"), (3, "section-opener"), (4, "scavenger-hunt")
    ]  # fmt: skip
    assert specs[1].params["badge"] == "مستكشف البيت" and specs[1].params["adventure"] == 1
    assert specs[3].activity == ActivityTags("home", together=True, minutes=10, challenge=True)
    assert specs[3].parent == ("مع {adult}",) and specs[3].skill == "الملاحظة والتركيز، العدّ والحساب البسيط"


def test_the_family_samples_are_valid_and_match_the_plan() -> None:
    samples = load(ROOT / SPECS["family"])
    assert isinstance(samples, FamilySamples)
    b, inserts = book_from(samples), inserts_from(samples)
    assert inserts is not None
    assert [p.number for p in b.pages] == [3, 6, 7, 8, 15, 18, 30, 64, 110, 112]
    assert [p.type for p in inserts.pages] == ["badge-sticker-sheet", "play-money"]
    assert b.geometry.page_w == 216 and b.geometry.page_h == 286
    assert book_problems(b) == [] and book_problems(inserts) == []
    build_pages(b, ASSETS)
    build_pages(inserts, ASSETS)
    if PLAN.exists():  # the samples show the plan's own pages
        from qamra_workbook.family import load as load_plan

        placed = {p.n: p for p in book_pages(load_plan(PLAN))}
        for spec in b.pages:
            plan_page = placed[spec.number].page
            assert (spec.type, spec.title, spec.instruction) == (
                plan_page.type,
                plan_page.title,
                plan_page.instruction,
            ), spec.id
