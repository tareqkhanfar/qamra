"""A typed name in an Arabic sentence (qamra_pdf.arabic_names): «يا أبا بكر», never «يا أبو بكر»."""

import pytest

from qamra_pdf.arabic_names import accusative, after, fill_name, fill_names, fix_vocatives, remark, unmark


@pytest.mark.parametrize(
    ("name", "form"),
    [
        ("أبو بكر", "أبا بكر"),
        ("ابو بكر", "ابا بكر"),  # the parent's spelling (no hamza) is kept
        ("أبو بكر الصديق", "أبا بكر الصديق"),
        ("ذو الفقار", "ذا الفقار"),
        ("أَبُو بَكْر", "أَبَا بَكْر"),  # the parent's tashkeel: the ب takes a fatha, the alif none
        ("أبُو بكر", "أبَا بكر"),
        ("ذُو الْفَقار", "ذَا الْفَقار"),
        ("  أبو علي", "  أبا علي"),
    ],
)
def test_a_name_with_abu_or_dhu_takes_alif_in_the_accusative(name: str, form: str) -> None:
    assert accusative(name) == form


@pytest.mark.parametrize(
    "name",
    [
        "سلمى",
        "محمد",
        "عبد الرحمن",
        "نور الهدى",
        "أبوبكر",  # one word: never split or respelled
        "أبو",  # not a name on its own
        "أبو ",
        "محمد أبو بكر",  # the first name takes the case; the rest is a surname
        "سلمى أبو غوش",
        "أبي بكر",  # typed in the genitive: left alone
        "أبيض",
        "ذوق",
        "Abu Bakr",
        "",
    ],
)
def test_every_other_name_is_left_as_typed(name: str) -> None:
    assert accusative(name) == name


def test_after_ya_and_at_an_accusative_slot_the_name_takes_alif() -> None:
    text = "رائِعٌ يا {child}! {ساعِدْ/ساعِدي} {child:acc}، ثُمَّ {child} نامَ. هَيّا {child}"
    assert fill_name(text, "child", "أبو بكر") == (
        "رائِعٌ يا أبا بكر! {ساعِدْ/ساعِدي} أبا بكر، ثُمَّ أبو بكر نامَ. هَيّا أبو بكر"
    )  # «هَيّا» ends in «يّا» but is not the vocative particle
    assert fill_name("وَ{أَنْتَ/أَنْتِ} يَا {child} {بَطَلُ/بَطَلَةُ}", "child", "أبو بكر") == (
        "وَ{أَنْتَ/أَنْتِ} يَا أبا بكر {بَطَلُ/بَطَلَةُ}"
    )
    assert fill_name("«{name:acc}!» {فَمَشَى/فَمَشَتْ} {name}", "name", "ذو الفقار") == (
        "«ذا الفقار!» {فَمَشَى/فَمَشَتْ} ذو الفقار"
    )


def test_a_name_without_abu_fills_every_slot_as_typed() -> None:
    text = "يا {child}، {child:acc} و{child}"
    assert fill_name(text, "child", "سلمى") == "يا سلمى، سلمى وسلمى"
    assert fill_name(text, "child", "عبد الرحمن") == "يا عبد الرحمن، عبد الرحمن وعبد الرحمن"
    assert fill_name("لا اسم هنا", "child", "أبو بكر") == "لا اسم هنا"
    assert fill_names("يا {name} وَ{companion:acc}", {"name": "أبو بكر", "companion": "قمّور"}) == (
        "يا أبا بكر وَقمّور"
    )


def test_a_placeholder_filled_with_itself_loses_only_its_mark() -> None:
    """How the Classic vowelization keeps its source (and its cache key) when a template gains a mark."""
    marked = "وَضَمَّتْ {name:acc} طَوِيلًا وَقالَتْ: يا {name}"
    assert fill_names(marked, {"name": "{name}", "companion": "{companion}"}) == unmark(marked, ("name",))
    assert unmark(marked, ("name",)) == "وَضَمَّتْ {name} طَوِيلًا وَقالَتْ: يا {name}"


def test_the_template_gives_its_marks_back_to_a_vowelized_text() -> None:
    template = "{ضَمَّ/ضَمَّتْ} {companion} {name:acc} وَقالَ: يا {name}"
    vowelized = "ضَمَّتْ {companion} {name} وَقَالَتْ: يَا {name}"
    slots = ("name", "companion")
    assert remark(vowelized, template, slots) == "ضَمَّتْ {companion} {name:acc} وَقَالَتْ: يَا {name}"
    assert remark("{name} وَ{companion}", template, slots) == "{name} وَ{companion}"  # not aligned: as is
    assert remark(vowelized, "", slots) == vowelized


def test_a_title_set_in_pieces_takes_the_case_after_ya() -> None:
    assert after("أَحْسَنْتَ يا ", "أبو بكر") == "أبا بكر"
    assert after("مُغامَراتُ ", "أبو بكر") == "أبو بكر"
    assert after("هَيّا ", "أبو بكر") == "أبو بكر"


def test_ai_text_gets_its_vocatives_fixed_for_the_childs_name() -> None:
    text = "قالَتْ ماما: «يَا أَبُو بَكْرٍ، تَعالَ!» ثُمَّ يا أبو بكر. أبو بكر هنا. يا أبو علي"
    assert fix_vocatives(text, "أبو بكر") == (
        "قالَتْ ماما: «يَا أَبَا بَكْرٍ، تَعالَ!» ثُمَّ يا أبا بكر. أبو بكر هنا. يا أبو علي"
    )  # the subject stays «أبو», another name is not touched
    assert fix_vocatives("يا أبو بكر", "سلمى") == "يا أبو بكر"
    assert fix_vocatives("يا سلمى", "سلمى") == "يا سلمى"
    assert fix_vocatives("هَيّا أبو بكر", "أبو بكر") == "هَيّا أبو بكر"
