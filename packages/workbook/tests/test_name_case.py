"""«يا أبا بكر», never «يا أبو بكر» (the bug of 2026-10-09): a name that starts with «أبو» takes «أبا» after
«يا» and in an accusative slot (`{child:acc}`, `{adult:acc}`, `{member:acc}`), in every activity book. The
name prints as typed everywhere else, and a name without «أبو» is never touched (`qamra_pdf.arabic_names`).
"""

import datetime as dt
import re
from pathlib import Path

import pytest
from qamra_workbook import islamic
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.islamic_sources import Resolver
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import RenderedPage, build_pages
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import SAMPLES as FAMILY_SAMPLES
from qamra_workbook.render.family import plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.islamic_volume import IslamicContext, check_volume, kit_for, volume_book
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.pages.family_front import split_name
from qamra_workbook.render.registry import Assets, PageContext
from qamra_workbook.render.samples import FamilySamples, assets_for
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Child, Family, Member, PageSpec, instruction_words
from qamra_workbook.render.workbook import volume_specs

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "content/workbook/samples/sample-character.png"  # an AI-drawn sample sheet, not a real person
ASSETS = Assets(LibraryStore())
DAY = dt.date(2026, 10, 9)
_M = "[ً-ْٰ]*"
WRONG = re.compile(f"(?<![؀-ۿ])ي{_M}ا{_M}\\s+[أا]{_M}ب{_M}و")  # «يا أبو», with any tashkeel
GENDERS = pytest.mark.parametrize("gender", ["m", "f"])  # «أبو بكر» is a boy's name; the rule is the same


def printed(pages: list[RenderedPage]) -> str:
    """Every text the pages print for this child: titles, instructions, the parents' box, the page data."""
    return "\n".join(" ".join([p.title, p.instruction, *p.parent, str(p.built.data)]) for p in pages)


# ---- the engine --------------------------------------------------------------------------------------------


@GENDERS
def test_the_child_and_the_family_take_their_case(gender: str) -> None:
    book = BookSpec(
        "family",
        "",
        Child("أبو بكر", gender),  # type: ignore[arg-type]
        (),
        DAY,
        family=Family("أبو غوش", (Member("سيدي", "أبو أحمد"),)),
    )
    assert book.personalize("رائِعٌ يا {child}!") == "رائِعٌ يا أبا بكر!"
    assert book.personalize("{أَحْسَنْتَ/أَحْسَنْتِ} يَا {child}!").endswith("يَا أبا بكر!")
    assert book.personalize("{ساعِدْ/ساعِدي} {child:acc} لِلْوُصولِ").endswith(" أبا بكر لِلْوُصولِ")
    assert book.personalize("{child} فِي سوقِ الخُضارِ") == "أبو بكر فِي سوقِ الخُضارِ"  # a subject
    assert book.personalize("نُخْبِرُ {adult:acc}، {ساعَدْتَ/ساعَدْتِ} {member:acc}").count("أبا أحمد") == 2
    assert book.personalize("مَعَ {adult}") == "مَعَ أبو أحمد"  # not an accusative slot: as typed
    assert book.personalize("فِي بَيْتِ عائِلَةِ {family_name}") == "فِي بَيْتِ عائِلَةِ أبو غوش"  # a surname
    assert book.personalize("هَيّا {child}") == "هَيّا أبو بكر"  # «هَيّا» is not «يا»


def test_a_name_without_abu_is_never_touched() -> None:
    book = BookSpec("journey", "", Child("سلمى", "f"), (), DAY)
    assert book.personalize("{أَحْسَنْتَ/أَحْسَنْتِ} يا {child}! {ساعِدْ/ساعِدي} {child:acc}") == (
        "أَحْسَنْتِ يا سلمى! ساعِدي سلمى"
    )
    for name in ("عبد الرحمن", "نور الهدى", "أبوبكر", "محمد أبو بكر"):
        assert BookSpec("journey", "", Child(name, "m"), (), DAY).personalize("يا {child}") == f"يا {name}"


def test_an_accusative_slot_is_one_word_and_a_title_in_pieces_takes_the_case() -> None:
    assert instruction_words("{ساعِدْ/ساعِدي} {child:acc} لِلْوُصولِ", "m") == 3
    assert instruction_words("نُخْبِرُ {adult:acc}", "f") == 2
    book = BookSpec("family", "", Child("أبو بكر", "m"), (), DAY)
    page = PageSpec("t", "title-page", 1, "front", "", "")
    ctx = PageContext(page, book, ASSETS)
    assert split_name(ctx, "أَحْسَنْتَ يا {child}!") == ("أَحْسَنْتَ يا ", "أبا بكر", "!")
    assert split_name(ctx, "مُغامَراتُ {child} مَعَ عائِلَتِهِ") == ("مُغامَراتُ ", "أبو بكر", " مَعَ عائِلَتِهِ")
    assert split_name(ctx, "{ساعِدْ/ساعِدي} {child:acc}") == ("ساعِدْ ", "أبا بكر", "")


# ---- the books ---------------------------------------------------------------------------------------------


@GENDERS
@pytest.mark.parametrize("stage", [1, 2, 3])
def test_the_journey_greets_and_helps_aba_bakr(stage: int, gender: str) -> None:
    interior, _ = stage_specs(Child("أبو بكر", gender), stage, name_en="Abu Bakr", day=DAY)  # type: ignore[arg-type]
    text = printed(build_pages(interior, ASSETS))
    assert not WRONG.search(text)
    assert "رائِعٌ يا أبا بكر!" in text  # «ماذا تَعَلَّمْتُ؟» pages
    assert ("ساعِدْ أبا بكر لِلْوُصولِ" if gender == "m" else "ساعِدي أبا بكر لِلْوُصولِ") in text  # the maze
    assert "أبو بكر" in text  # the owner page and the map keep the name as typed
    if stage in (1, 2):
        assert ("أَحْسَنْتَ يا أبا بكر!" if gender == "m" else "أَحْسَنْتِ يا أبا بكر!") in text
    if stage == 3:
        assert "راقِبوا أبا بكر،" in text  # the observation card for the grown-ups


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_the_journey_keeps_a_girls_name(stage: int) -> None:
    interior, _ = stage_specs(Child("سلمى", "f"), stage, name_en="Salma", day=DAY)
    text = printed(build_pages(interior, ASSETS))
    assert "رائِعٌ يا سلمى!" in text and "ساعِدي سلمى لِلْوُصولِ" in text


def _family_book(child: Child, family: Family | None = None) -> BookSpec:
    samples = load_samples(FAMILY_SAMPLES)
    assert isinstance(samples, FamilySamples)
    plan = load_family(FAMILY_PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    return family_spec(tuple(specs), child, family or samples.family.spec(), day=DAY)


@GENDERS
def test_the_family_book_names_aba_bakr_and_his_grandfather_in_the_accusative(gender: str) -> None:
    grandpa = Family("الخطيب", (Member("سيدي", "أبو أحمد"),), "رام الله")
    text = printed(build_pages(_family_book(Child("أبو بكر", gender), grandpa), ASSETS))  # type: ignore[arg-type]
    assert not WRONG.search(text)
    assert "يا أبا بكر،" in text  # «هَيّا يا أبا بكر، جَهِّزْ عَيْنَيْكَ»
    assert "امنحوا أبا بكر شارة" in text and "اشكروا أبا بكر على" in text
    assert "نُخْبِرُ أبا أحمد" in text  # {adult:acc}
    assert ("اسْأَلْ أبا أحمد" if gender == "m" else "اسْأَلي أبا أحمد") in text
    assert ("ساعَدْتَ فيها أبا أحمد" if gender == "m" else "ساعَدْتِ فيها أبا أحمد") in text  # {member:acc}


def test_the_family_book_keeps_a_girls_name() -> None:
    text = printed(build_pages(_family_book(Child("سلمى", "f")), ASSETS))
    assert "يا سلمى،" in text and "اشكروا سلمى على" in text and "أبا" not in text


@GENDERS
def test_the_foundation_certificate_congratulates_aba_bakr(gender: str, tmp_path: Path) -> None:
    book, *_ = volume_specs(Child("أبو بكر", gender), "kg1", 3, name_en="Abu Bakr", day=DAY)  # type: ignore[arg-type]
    text = printed(build_pages(book, assets_for(book, tmp_path)))
    assert "مَبْروكٌ يا أبا بكر!" in text and not WRONG.search(text)


@GENDERS
def test_the_islamic_book_addresses_aba_bakr(gender: str, tmp_path: Path) -> None:
    child = Child("أبو بكر", gender, SHEET)  # type: ignore[arg-type]
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, "V1", resolver, build=False)
    context = IslamicContext(resolver, kit_for(child.character_sheet, tmp_path / "kit"), "preview", DAY)
    book = volume_book(plan, content, context, child)
    text = printed(build_pages(book, assets_for(book, tmp_path)))
    assert "يَا أبا بكر" in text and not WRONG.search(text)
