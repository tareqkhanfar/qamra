"""«دوسية التأسيس» for a boy and for a girl (the gender audit of 9 October 2026): every printed text of
every page of the six volumes, the answer keys and the covers, as the HTML prints it for «يوسف» (m) and
«ليان» (f). No `{masc/fem}` variant is left unresolved, no Arabic line takes a Latin comma, and no form of
the other gender slips into a child's book. The targeted tests below keep each class of slip the audit fixed
from coming back: the openers' objectives in the child's own (neutral) first person, the grown-ups' lines
about the child (the pen checklist, the score box, the answer key) in the child's gender, no gendered ḥāl in
a first-person skill line, Arabic lists joined with «وَ», a key that never points «رَسَمَتْ سَلْمى» to a
masculine verb."""

from __future__ import annotations

import datetime as dt
import functools
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from qamra_workbook.curriculum import load
from qamra_workbook.render.engine import answer_key_html, book_html, build_pages
from qamra_workbook.render.foundation import from_curriculum, volume_of
from qamra_workbook.render.foundation_text import (
    joined,
    letters_head,
    objective_as_child,
    shapes_title,
    third_person_left,
)
from qamra_workbook.render.samples import assets_for
from qamra_workbook.render.spec import Child
from qamra_workbook.render.workbook import volume_specs

CURRICULUM = Path(__file__).resolve().parents[3] / "content/workbook/curriculum"
BOY, GIRL = Child("يوسف", "m"), Child("ليان", "f")
NAMES_EN = {"يوسف": "Yusuf", "ليان": "Layan"}
VOLUMES = [(level, n) for level in ("kg1", "kg2") for n in (1, 2, 3)]
DAY = dt.date(2026, 10, 9)


class _Text(HTMLParser):
    """The printed text of a page: every text node outside <style>/<script>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.out: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.skip += tag in ("style", "script")

    def handle_endtag(self, tag: str) -> None:
        self.skip -= tag in ("style", "script")

    def handle_data(self, data: str) -> None:
        line = " ".join(data.split())
        if line and not self.skip:
            self.out.append(line)


def printed(html: str) -> list[str]:
    parser = _Text()
    parser.feed(html)
    return parser.out


@functools.cache
def volume_text(level: str, number: int, gender: str) -> dict[str, list[str]]:
    """Every printed line of the volume for the boy or the girl: the interior, the answer key, the covers."""
    child = BOY if gender == "m" else GIRL
    book, cover, _, _ = volume_specs(child, level, number, name_en=NAMES_EN[child.name], day=DAY)
    assets = assets_for(book, Path("/nonexistent"))  # no character sheet: the picture library only
    pages = build_pages(book, assets)
    return {
        "interior": printed(book_html(book, pages, assets)),
        "key": printed(answer_key_html(book, pages, assets)),
        "cover": printed(book_html(cover, build_pages(cover, assets), assets)),
    }


def lines(level: str, number: int, gender: str) -> list[str]:
    return [line for part in volume_text(level, number, gender).values() for line in part]


def everything(gender: str) -> str:
    return "\n".join(line for level, number in VOLUMES for line in lines(level, number, gender))


LATIN_COMMA = re.compile(r"[؀-ۿ٠-٩],")
# a word that ends in the other gender's «ـكَ» / «ـكِ» (the pronoun «you»), but «ذلِكَ», a lone «كَ» or «كِ»
# (a syllable card), and the masculine imperative's helping kasra before «ال» («أَمْسِكِ القَلَمَ»)
MASCULINE_KA = re.compile(r"(\S+كَ)(?=[\s،.:!؟»]|$)")
FEMININE_KI = re.compile(r"(\S+كِ)(?=[\s،.:!؟»]|$)(?!\s+ا)")
NOT_THE_PRONOUN = {"ذلِكَ", "ذَلِكَ", "كَذلِكَ"}
BOY_ONLY = ("الطفل وهو", "رأى الطفل", "يقرأ الطفل", "سمّاه الطفل", "أَنْتَ ", "أَحْسَنْتَ", "وشخصيته", "لِصَديقي")
GIRL_ONLY = ("الطفلة", "رأت ", "تقرأ الطفلة", "سمّته", "أَنْتِ ", "أَحْسَنْتِ", "وشخصيتها", "لِصَديقَتي")


def has(text: str, word: str) -> bool:
    """`word` in `text` as a whole word («وشخصيته» is not in «وشخصيتها»)."""
    return re.search(re.escape(word) + r"(?![ء-ْ])", text) is not None


@pytest.mark.parametrize(("level", "number"), VOLUMES)
def test_every_printed_line_is_resolved_for_a_boy_and_a_girl(level: str, number: int) -> None:
    for gender in ("m", "f"):
        for line in lines(level, number, gender):
            assert "{" not in line and "}" not in line, f"{level}-v{number} ({gender}): {line}"
            assert not LATIN_COMMA.search(line), f"{level}-v{number} ({gender}): Latin comma in «{line}»"


@pytest.mark.parametrize(("level", "number"), VOLUMES)
def test_no_form_of_the_other_gender_slips_into_a_childs_book(level: str, number: int) -> None:
    boy, girl = "\n".join(lines(level, number, "m")), "\n".join(lines(level, number, "f"))
    for word in GIRL_ONLY:
        assert not has(boy, word), f"{level}-v{number}: the boy's book prints «{word}»"
    for word in BOY_ONLY:
        assert not has(girl, word), f"{level}-v{number}: the girl's book prints «{word}»"
    assert not [w for w in MASCULINE_KA.findall(girl) if w not in NOT_THE_PRONOUN], f"{level}-v{number}"
    assert not FEMININE_KI.findall(boy), f"{level}-v{number}"


def test_the_books_speak_to_each_child_in_their_gender() -> None:
    """The same instruction, title and praise, both ways (the checks above would pass on two equal books)."""
    boy, girl = everything("m"), everything("f")
    for masculine, feminine in (
        ("تَتَبَّعِ اسْمَكَ، ثُمَّ اكْتُبْهُ وَحْدَكَ", "تَتَبَّعي اسْمَكِ، ثُمَّ اكْتُبيهِ وَحْدَكِ"),
        ("أَحْسَنْتَ يا بَطَلُ!", "أَحْسَنْتِ يا بَطَلَةُ!"),
        ("باسم يوسف وشخصيته", "باسم ليان وشخصيتها"),
    ):
        assert masculine in boy and feminine in girl and masculine not in girl and feminine not in boy


# ---- the classes of slips the audit fixed ----


def objectives() -> list[str]:
    return [
        item
        for level in ("kg1", "kg2")
        for volume in load(CURRICULUM / f"{level}.yaml").volumes
        for items in volume.objectives.values()
        for item in items
    ]


def test_the_openers_objectives_are_in_the_childs_own_first_person() -> None:
    """Under «في هذا الجزء سأتعلّم» the child says what they will learn: «أتعرّف…», never «يتعرّف…» (masculine
    about the child, in a girl's book too)."""
    for objective in objectives():
        said = objective_as_child(objective)
        assert said.startswith("أ") and not third_person_left(said), f"{objective} → {said}"
    assert objective_as_child("يكتب وحده الحروف ويتتبّعها") == "أكتب وحدي الحروف وأتتبّعها"
    assert (
        objective_as_child("يلاحظ ٣ فروق بين صورتين ويتذكّر ما رآه")
        == "ألاحظ ٣ فروق بين صورتين وأتذكّر ما رأيته"
    )
    assert objective_as_child("يتعرّف على الحروف ويكتبها، فيكتمل عنده الحروف") == (
        "أتعرّف على الحروف وأكتبها، فتكتمل عندي الحروف"
    )
    assert objective_as_child("يلوّن رسمًا ويرسم نفسه وأصدقاءه.") == "ألوّن رسمًا وأرسم نفسي وأصدقائي."
    assert objective_as_child("يتتبّع كل حرف ويكتبه مستقلًّا") == "أتتبّع كل حرف وأكتبه وحدي"
    # what is not about the child stays as it is
    assert objective_as_child("يختار ما يحتاجه كل موقف") == "أختار ما يحتاجه كل موقف"
    assert objective_as_child("يستعمل كلمات المكان: يمين ويسار.") == "أستعمل كلمات المكان: يمين ويسار."
    assert objective_as_child("يجد الشيء الذي لا ينتمي إلى مجموعته") == "أجد الشيء الذي لا ينتمي إلى مجموعته"


def test_a_rendered_opener_prints_the_first_person_objectives() -> None:
    plan = load(CURRICULUM / "kg2.yaml")
    volume = volume_of(plan, 1)
    openers = [from_curriculum(p, plan, volume) for p in volume.pages if p.type == "unit-opener"]
    assert openers
    for page in openers:
        assert all(str(o).startswith("أ") for o in page.params["objectives"]), page.id
    for gender in ("m", "f"):
        assert "أتعرّف على الحروف من الألف إلى الذال" in "\n".join(lines("kg2", 1, gender))
        assert "يتعرّف على" not in "\n".join(volume_text("kg2", 1, gender)["interior"])


def test_no_first_person_skill_line_carries_a_gendered_hal() -> None:
    """«أتتبّع العدد ثلاثة مبتدئًا…» is masculine in a girl's book: the skill lines say «بدءًا من…»."""
    gendered = re.compile(r"\b(?:مبتدئ|منتبه|جالس|واقف|مستعد|مسرور)[ًاةه]")
    for level in ("kg1", "kg2"):
        for volume in load(CURRICULUM / f"{level}.yaml").volumes:
            for page in volume.pages:
                assert not gendered.search(page.skill), f"{level}-v{volume.volume}-p{page.n}: {page.skill}"


def test_the_grown_ups_lines_about_the_child_follow_the_childs_gender() -> None:
    """The pen checklist, the score box and the answer key talk about the child: «لاحظوا الطفلة وهي تتتبّع»,
    «أتقنتها / تتحسّن / تحتاج تدريبًا», «أتقنت المهارة», «رأت الطفلة», «تقرأ الطفلة», «سمّته الطفلة»."""
    boy, girl = everything("m"), everything("f")
    pairs = (
        ("لاحظوا الطفل وهو يتتبّع", "لاحظوا الطفلة وهي تتتبّع"),
        ("أتقنها", "أتقنتها"),
        ("يتحسّن", "تتحسّن"),
        ("أتقن المهارة", "أتقنت المهارة"),
        ("يحتاج قليلًا من التدريب", "تحتاج قليلًا من التدريب"),
        ("رأى الطفل:", "رأت الطفلة:"),
        ("يقرأ الطفل:", "تقرأ الطفلة:"),
        ("يقرأ الطفل كل صف:", "تقرأ الطفلة كل صف:"),
        ("علامة تحت كل حرف سمّاه الطفل", "علامة تحت كل حرف سمّته الطفلة"),
        ("يقرأ الحرف مع الفتحة", "تقرأ الحرف مع الفتحة"),
    )
    for masculine, feminine in pairs:
        assert masculine in boy and feminine in girl, (masculine, feminine)
        assert masculine not in girl and feminine not in boy, (masculine, feminine)
    key_boy = "\n".join(volume_text("kg2", 3, "m")["key"])
    key_girl = "\n".join(volume_text("kg2", 3, "f")["key"])
    assert "يكتب: " in key_boy and "تكتب: " in key_girl and "يكتب: " not in key_girl


def test_a_word_problem_told_by_a_girl_gives_to_her_friend() -> None:
    boy, girl = "\n".join(lines("kg2", 3, "m")), "\n".join(lines("kg2", 3, "f"))
    assert "مِنْها لِصَديقي." in boy and "مِنْها لِصَديقَتي." in girl


def test_the_sentence_key_never_points_a_girl_to_a_masculine_verb() -> None:
    key = "\n".join(volume_text("kg2", 3, "f")["key"])
    assert "رَسَمَتْ سَلْمى ← صورة الرسم" in key and "← رَسَمَ" not in key


def test_arabic_lists_join_every_item_with_wa() -> None:
    assert joined(["الهاءِ", "الواوِ", "الياءِ"]) == "الهاءِ وَالواوِ وَالياءِ"
    assert letters_head(["ب", "ت", "ث"]) == "حُروفُ الباءِ وَالتّاءِ وَالثّاءِ"
    assert shapes_title(["circle", "square", "triangle", "rectangle"]).endswith("وَالمُسْتَطيلُ")
    assert shapes_title() == "الدّائِرَةُ وَالمُرَبَّعُ وَالمُثَلَّثُ"
    text = everything("f")
    assert "أَيْنَ حُروفُ الهاءِ وَالواوِ وَالياءِ؟" in text and "الهاءِ، الواوِ" not in text
    assert "أَكْتُبُ العَدَدَيْنِ ٩ وَ١٠" in text and "أَكْتُبُ الأَعْدادَ ٩ وَ١٠" not in text  # two: the dual
    assert "ما المُخْتَلِفُ؟" in text and "مَنِ المُخْتَلِفُ؟" not in text  # things: «ما»
