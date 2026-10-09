"""A typed name in an Arabic sentence (qamra_pdf.arabic_names): «يا أبا بكر», «لِأبي بكر», never «يا أبو
بكر»."""

import pytest

from qamra_pdf.arabic_names import (
    accusative,
    after,
    after_lam,
    case_forms,
    fill_name,
    fill_names,
    fix_genitives,
    fix_vocatives,
    genitive,
    has_article,
    in_case,
    remark,
    unmark,
    with_helping_vowel,
)
from qamra_pdf.lettering import name_units


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


# ---- the genitive ----


@pytest.mark.parametrize(
    ("name", "form"),
    [
        ("أبو بكر", "أبي بكر"),
        ("ابو بكر", "ابي بكر"),  # the parent's spelling (no hamza) is kept
        ("أبو بكر الصديق", "أبي بكر الصديق"),
        ("ذو الفقار", "ذي الفقار"),
        ("أَبُو بَكْر", "أَبِي بَكْر"),  # the parent's tashkeel: the ب takes a kasra, the ي none
        ("أبُو بكر", "أبِي بكر"),
        ("ذُو الْفَقار", "ذِي الْفَقار"),
        ("  أبو علي", "  أبي علي"),
    ],
)
def test_a_name_with_abu_or_dhu_takes_ya_in_the_genitive(name: str, form: str) -> None:
    assert genitive(name) == form
    assert in_case(name, ":gen") == in_case(name, "gen") == form
    assert in_case(name, ":acc") == accusative(name)
    assert in_case(name, "") == name


@pytest.mark.parametrize(
    "name",
    [
        "سلمى",
        "محمد",
        "عبد الرحمن",
        "أبوبكر",
        "أبو",
        "محمد أبو بكر",
        "سلمى أبو غوش",
        "أبي بكر",
        "Abu Bakr",
        "",
    ],
)
def test_every_other_name_is_left_as_typed_in_the_genitive(name: str) -> None:
    assert genitive(name) == name
    assert case_forms(name) == ((name,) if accusative(name) == name else (name, accusative(name)))


def test_a_genitive_slot_takes_ya_and_joins_a_lam_before_it() -> None:
    text = "هذا الكِتابُ لِـ{child:gen}، رِحْلَةُ {child:gen} مَعَ {child:gen}. يا {child}، {child:acc} و{child}"
    assert fill_name(text, "child", "أبو بكر") == (
        "هذا الكِتابُ لِأبي بكر، رِحْلَةُ أبي بكر مَعَ أبي بكر. يا أبا بكر، أبا بكر وأبو بكر"
    )  # «لِـ» + an alif: the لا ligature, never «لِـأبي»
    assert fill_name(text, "child", "سلمى") == (
        "هذا الكِتابُ لِـسلمى، رِحْلَةُ سلمى مَعَ سلمى. يا سلمى، سلمى وسلمى"
    )  # any other letter keeps the «ـ»
    assert fill_name("لِـ{child:gen}", "child", "محمد") == "لِـمحمد"
    assert fill_name("لِـ{child:gen}", "child", "أحمد") == "لِأحمد"
    assert fill_name("لـ{child:gen}", "child", "إياد") == "لإياد"
    assert fill_name("لِـ{child:gen}", "child", "المعتصم") == "لِلمعتصم"  # «ال» after «لِـ» is written «لل»
    assert fill_name("بِـ{child:gen}", "child", "أبو بكر") == "بِـأبي بكر"  # only «ل» makes a ligature
    assert fill_name("{child:gen}", "child", "") == ""
    assert fill_names("إلى {name:gen} وَ{companion:gen}", {"name": "ذو الفقار", "companion": "أبو شنب"}) == (
        "إلى ذي الفقار وَأبي شنب"
    )


def test_the_genitive_mark_is_kept_out_of_a_cached_source_and_put_back() -> None:
    template = "إلى {name:gen}، {ضَمَّ/ضَمَّتْ} {name:acc} لِـ{companion:gen}"
    plain = "إلى {name}، {ضَمَّ/ضَمَّتْ} {name} لِـ{companion}"
    assert unmark(template, ("name", "companion")) == plain
    assert fill_names(template, {"name": "{name}", "companion": "{companion}"}) == plain
    vowelized = "إِلَى {name}، ضَمَّتْ {name} لِـ{companion}"
    assert remark(vowelized, template, ("name", "companion")) == (
        "إِلَى {name:gen}، ضَمَّتْ {name:acc} لِـ{companion:gen}"
    )


def test_ai_text_gets_its_genitives_fixed_after_a_preposition() -> None:
    text = (
        "ذَهَبَ لِأَبُو بَكْرٍ وَمَعَ أَبُو بَكْرٍ، إلى أبو بكر، لـأبو بكر، عِنْدَ أبو بكر، بأبو بكر. "
        "مَنْ أبو بكر؟ مِنْ أبو بكر. عن أبو علي. حقيبة أبو بكر. قَبَّلَ أبو بكر. أبو بكر هنا."
    )
    assert fix_genitives(text, "أبو بكر") == (
        "ذَهَبَ لِأَبِي بَكْرٍ وَمَعَ أَبِي بَكْرٍ، إلى أبي بكر، لأبي بكر، عِنْدَ أبي بكر، بأبي بكر. "
        "مَنْ أبو بكر؟ مِنْ أبي بكر. عن أبو علي. حقيبة أبو بكر. قَبَّلَ أبو بكر. أبو بكر هنا."
    )  # «مَنْ» (who), another name, an iḍāfa, a verb before a subject and the subject: untouched
    assert fix_genitives("مع ذو الفقار", "ذو الفقار") == "مع ذي الفقار"
    assert fix_genitives("من أبو بكر؟", "أبو بكر") == "من أبو بكر؟"  # a bare «من» may be «مَنْ» (who)
    assert fix_genitives("مع أبو بكر", "سلمى") == "مع أبو بكر"
    assert fix_genitives("مع سلمى", "سلمى") == "مع سلمى"


def test_a_title_finds_the_name_in_its_case() -> None:
    assert name_units("يوم تخرّج أبي بكر", "أبو بكر") == (["يوم", "تخرّج", "أبي بكر"], 2)
    assert name_units("يا أبا بكر", "أبو بكر")[1] == 1
    assert name_units("يوم تخرّج سلمى", "سلمى")[1] == 2
    assert name_units("يوم تخرّج أبي علي", "أبو بكر")[1] is None


# ---- names with the article ----


@pytest.mark.parametrize(
    ("name", "article"),
    [
        *[("المعتصم", True), ("الْحَسَن", True), ("الليث", True), ("الجود", True), ("الين", False)],
        *[("الاء", False), ("الهام", False), ("الياس", False), ("أحمد", False), ("سلمى", False), ("", False)],
    ],
)
def test_a_name_has_the_article_or_not(name: str, article: bool) -> None:
    assert has_article(name) is article


def test_lam_joins_a_name_with_the_article_and_keeps_the_others_whole() -> None:
    assert fill_name("لِـ{child:gen}", "child", "الليث") == "لِليث"  # «ل» + «الل» is written «لل»
    assert fill_name("لِـ{child:gen}", "child", "اللؤلؤة") == "لِلؤلؤة"
    assert fill_name("لِـ{child:gen}", "child", "الْمُعْتَصِم") == "لِلْمُعْتَصِم"
    assert (
        fill_name("لِـ{child:gen}", "child", "الين") == "لِالين"
    )  # no article: the لا ligature, the name whole
    assert fill_name("لِـ{child:gen}", "child", "الاء") == "لِالاء"
    assert after_lam("سلمى") is None and after_lam("أبي بكر") == "أبي بكر"


def test_a_sukun_before_a_name_with_the_article_takes_the_helping_vowel() -> None:
    text = "هَمَسَتْ {name} وَضَمَّتْ {name:acc} مِنْ {name:gen} عَلَيْكُمْ {name} أَوْ {name} فِيْ {name}"
    assert fill_name(text, "name", "الجود") == (
        "هَمَسَتِ الجود وَضَمَّتِ الجود مِنَ الجود عَلَيْكُمُ الجود أَوِ الجود فِي الجود"
    )
    for name in ("سلمى", "الين", "أبو بكر"):  # no article: every sukun stays
        assert "هَمَسَتْ" in fill_name(text, "name", name) and "مِنْ" in fill_name(text, "name", name)
    assert with_helping_vowel("هَمَسَتْ ", "الحسن") == "هَمَسَتِ " and with_helping_vowel("هَمَسَتْ ", "سلمى") == "هَمَسَتْ "


def test_ya_with_a_conjunction_is_a_vocative() -> None:
    assert fill_name("وَيا {child}، فَيَا {child}", "child", "أبو بكر") == "وَيا أبا بكر، فَيَا أبا بكر"
    assert fill_name("هَيّا {child}", "child", "أبو بكر") == "هَيّا أبو بكر"
