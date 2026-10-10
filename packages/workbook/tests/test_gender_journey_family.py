"""«رحلتي الأولى للتعلّم» and «مغامراتي مع عائلتي» for a boy and for a girl (the gender audit of 2026-10-09).

Every string the pages print is read out of the rendered HTML, page by page, for «يوسف» and for «ليان»: each
journey stage (interior, cover, sticker sheet and the answer key) and the family book (interior, cover and
its inserts, with two families that list the same people in opposite order, so that the grown-up a page
names is a man in one book and a woman in the other). Then:

- no line keeps a placeholder or a `{masc/fem}` pair;
- a line printed alike for both children never speaks to the child in one gender (a fixed «ابدأ», «اسمع»,
  «امسح الرمز», a «ـكَ» or «ـكِ», «ليسمع الطفل»);
- the grown-ups' skill line and the answer key speak of the child in the child's own gender («تتعرّف على
  كتابها»), or in the first person plural («نلوّن ٣ فقط»), and name colours and shapes in Arabic;
- the audio player's titles and scripts, the same for every child, use no word that the books print only
  in one gender.
"""

import asyncio
import re
from collections.abc import Iterator
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.journey import load as load_journey
from qamra_workbook.journey_book import AUDIO, PLAN, built_stages
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import cover_specs, insert_sheets, plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import BookSpec, Child, Family, Member
from qamra_workbook.render.stickers import sheet_book

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
BOY, GIRL = Child("يوسف", "m"), Child("ليان", "f")
PEOPLE = (
    ("بابا", ""),
    ("ماما", ""),
    ("سيدي", ""),
    ("ستّي", ""),
    ("أخي", "كرم"),
    ("أختي", "سلمى"),
)  # a man, a woman, a man…: the boy's family in this order, the girl's with each pair swapped
FAMILY = {
    "m": Family("الخطيب", tuple(Member(role, name) for role, name in PEOPLE), "رام الله"),
    "f": Family(
        "الخطيب",
        tuple(Member(role, name) for k in range(0, 6, 2) for role, name in (PEOPLE[k + 1], PEOPLE[k])),
        "رام الله",
    ),
}
KEY = "مفتاح: "  # an answer-key line, after the page's own lines

Dump = dict[str, list[str]]  # page id → its printed lines


class _Lines(HTMLParser):
    """The visible text of each `[data-page]` section, one line per block element."""

    BLOCK = frozenset(
        {
            "div",
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "ul",
            "ol",
            "section",
            "header",
            "footer",
            "main",
        }
        | {"article", "aside", "td", "th", "tr", "br", "figure", "figcaption", "text", "label", "svg", "g"}
    )
    HIDDEN = frozenset({"style", "script", "head", "title", "defs"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: Dump = {}
        self.page = ""
        self.hidden = 0
        self.text: list[str] = []

    def flush(self) -> None:
        line = re.sub(r"\s+", " ", "".join(self.text)).strip()
        self.text = []
        if line and self.page:
            self.pages[self.page].append(line)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.HIDDEN:
            self.hidden += 1
            return
        page = dict(attrs).get("data-page")
        if tag in self.BLOCK or page:
            self.flush()
        if tag == "section" and page:
            self.page = page
            self.pages[page] = []

    def handle_endtag(self, tag: str) -> None:
        if tag in self.HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        elif tag in self.BLOCK:
            self.flush()

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.text.append(data)


def dump(book: BookSpec) -> Dump:
    """Every line each page prints for this child, then its answer-key lines."""
    pages = build_pages(book, ASSETS)
    parser = _Lines()
    html = book_html(book, pages, ASSETS)
    parser.feed(html[html.index("<body") :])
    parser.flush()
    for p in pages:
        parser.pages.setdefault(p.spec.id, []).extend(KEY + line for line in p.built.answer or [])
    return parser.pages


def journey_books(child: Child) -> Iterator[tuple[str, BookSpec]]:
    for stage in built_stages(ROOT):
        interior, cover = stage_specs(child, stage)
        yield f"s{stage}-interior", interior
        yield f"s{stage}-cover", cover
        yield f"s{stage}-stickers", sheet_book(interior)


def family_books(child: Child) -> Iterator[tuple[str, BookSpec]]:
    plan = load_family(ROOT / FAMILY_PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    family = FAMILY[child.gender]
    yield "family-interior", family_spec(tuple(specs), child, family)
    yield "family-cover", family_spec(tuple(cover_specs(plan)), child, family)
    for name, sheets in insert_sheets(plan):
        yield f"family-{name}", family_spec(tuple(sheets), child, family)


@pytest.fixture(scope="module")
def dumps() -> dict[str, tuple[Dump, Dump]]:
    """Each book part as (the boy's dump, the girl's dump)."""
    out: dict[str, tuple[Dump, Dump]] = {}
    for books in (journey_books, family_books):
        boy, girl = dict(books(BOY)), dict(books(GIRL))
        out |= {part: (dump(boy[part]), dump(girl[part])) for part in boy}
    return out


def alike(boy: list[str], girl: list[str]) -> list[str]:
    """The lines a page prints the same way for both children (aligned in order)."""
    match = SequenceMatcher(a=boy, b=girl, autojunk=False)
    return [line for op, i, j, *_ in match.get_opcodes() if op == "equal" for line in boy[i:j]]


def bare(text: str) -> str:
    return strip_tashkeel(text).replace("ـ", "")


# ---- every line ----------------------------------------------------------------------------------------


def test_every_part_is_dumped_for_both_children(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    assert {"s1-interior", "s2-cover", "s3-stickers", "family-interior", "family-cover"} <= set(dumps)
    assert any(part.startswith("family-") and "stickers" in part for part in dumps)  # the inserts
    for part, (boy, girl) in dumps.items():
        assert boy.keys() == girl.keys() and boy, part
    lines = sum(len(lines) for boy, _ in dumps.values() for lines in boy.values())
    assert lines > 6000  # the three stages and the family book, page by page


def test_no_line_keeps_a_placeholder(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    left = [
        (part, page, line)
        for part, pair in dumps.items()
        for book in pair
        for page, lines in book.items()
        for line in lines
        if re.search(r"[{}]", line)
    ]
    assert left == []


# a word that ends in the 2nd-person «ـكَ»/«ـكِ», with its tashkeel; the letter «كَ» of a letter page alone
_YOU = re.compile(r"[ء-ي][ً-ْ]*ك[َِ](?=$|[\s،؟!.:»…])")
_FIXED = (  # what used to print alike for both children (a boy's word in the girl's book, or the reverse)
    "ابدأ من",
    "ابدئي من",
    "اسمع صوت الحرف",
    "امسح الرمز",
    "امسحي الرمز",
    "ليسمع الطفل",
    "رأى:",
    "رأت:",
    "يلوّن",
    "تلوّن",
    "يتذكّر الصور",
    "يقرأ:",
    "تقرأ:",
    "رائع يا",
    "رائعة يا",
)


def test_a_line_printed_alike_for_both_children_never_speaks_to_one_gender(
    dumps: dict[str, tuple[Dump, Dump]],
) -> None:
    wrong = []
    for part, (boy, girl) in dumps.items():
        for page, lines in boy.items():
            for line in alike(lines, girl[page]):
                plain = bare(line)
                if _YOU.search(line) or any(word in plain for word in _FIXED):
                    wrong.append(f"{part} {page}: {line}")
    assert wrong == []


# ---- the grown-ups' skill line and the answer key ---------------------------------------------------------

_EXCEPT = ("تقييم:", "يقيّم الكبار")  # the assessment pages name what is assessed, and who assesses it
_HIS = ("كتابه", "يده", "بإصبعه", "اسمه", "وحده", "بنفسه", "وجهه", "عينه", "بعينه", "صورته", "بكلماته")


def test_every_skill_line_speaks_of_the_child_in_their_gender() -> None:
    plan = load_journey(ROOT / PLAN)
    for stage in plan.stages:
        for page in stage.pages:
            skill = page.skill
            if not re.search("[ء-ي]", skill) or skill.startswith(_EXCEPT):
                continue
            boy, girl = BOY.personalize(skill), GIRL.personalize(skill)
            assert boy != girl, f"S{stage.stage} p{page.n}: the skill line does not follow the child: {skill}"
            # the verb that opens the line, after a writing level («مستوى الكتابة ٣: تتتبع …»)
            first = (girl.split(":", 1)[1] if girl.startswith("مستوى") else girl).split()[0]
            assert not first.startswith("ي"), f"S{stage.stage} p{page.n}: «{girl}»"
            assert not set(re.findall(r"[ء-ي]+", girl)) & set(_HIS), f"S{stage.stage} p{page.n}: «{girl}»"


def test_the_girls_skill_lines_and_answer_keys_never_speak_of_a_boy(
    dumps: dict[str, tuple[Dump, Dump]],
) -> None:
    boy_s1, girl_s1 = dumps["s1-interior"]
    assert "تتعرّف على كتابها وتترك بصمة يدها" in girl_s1["journey-s1-p1"]
    assert "يتعرّف على كتابه ويترك بصمة يده" in boy_s1["journey-s1-p1"]
    assert KEY + "رأت: شَمْس، كُرَة، بَطَّة" in girl_s1["journey-s1-p8"]
    assert KEY + "رأى: شَمْس، كُرَة، بَطَّة" in boy_s1["journey-s1-p8"]
    for part, (_, girl) in dumps.items():
        keys = [line for lines in girl.values() for line in lines if line.startswith(KEY)]
        for line in keys:
            plain = bare(line)
            assert not re.search(r"(^|[\s:])(يلوّن|يتذكّر|يقرأ|يقلب|رأى)(?=[\s:]|$)", plain), (part, line)


def test_answer_keys_name_colours_and_shapes_in_arabic(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    _, girl = dumps["s1-interior"]
    assert KEY + "البالون الأحمر: للطفل ٢ من اليمين" in girl["journey-s1-p25"]
    _, girl = dumps["s2-interior"]
    assert any(line.startswith(KEY + "الطائرة الحمراء:") for line in girl["journey-s2-p9"])
    assert KEY + "٢ من كل نوع: دائرة حمراء، دائرة زرقاء، مثلث أحمر، مثلث أزرق" in girl["journey-s2-p7"]
    latin = re.compile(r"\b(red|blue|yellow|green|pink|circle|square|triangle)\b")
    for stage in (1, 2, 3):
        _, girl = dumps[f"s{stage}-interior"]
        for page, lines in girl.items():
            for line in lines:
                said = line.removeprefix(KEY)
                if line.startswith(KEY) and re.search("[ء-ي]", said):  # an Arabic key (not an English page's)
                    assert not latin.search(said), (page, line)


def test_the_key_agrees_with_what_the_title_compares(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    _, s1 = dumps["s1-interior"]
    _, s2 = dumps["s2-interior"]
    _, s3 = dumps["s3-interior"]
    assert KEY + "١: دِيك ودِيك — متشابهان" in s1["journey-s1-p33"]  # two sounds
    assert KEY + "١: قَمَر وقَمَر — متشابهتان" in s2["journey-s2-p12"]  # two words
    assert "أَسْمَعُ الكَلِمَةَ" in s2["journey-s2-p18"]  # its review panel plays one word, as its audio
    assert KEY + "أَسْمَعُ الكَلِمَةَ: شمس" in s2["journey-s2-p18"]
    assert KEY + "قَمَر وشَجَر" in s3["journey-s3-p11"]  # the words the audio says rhyme


# ---- the labels the pages draw ---------------------------------------------------------------------------


def test_the_labels_and_the_cheer_follow_the_child(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    boy, girl = dumps["s2-interior"]
    finger = "journey-s2-p30"  # the alif's finger-trace page
    assert "ابْدَأْ مِنَ النُّقْطَةِ الخَضْراءِ" in boy[finger]
    assert "ابْدَئي مِنَ النُّقْطَةِ الخَضْراءِ" in girl[finger]
    assert any(line.startswith("اسْمَعْ صَوْتَ الحَرْفِ") and "ليسمع طفلكم «أ»" in line for line in boy[finger])
    assert any(line.startswith("اسْمَعي صَوْتَ الحَرْفِ") and "لتسمع طفلتكم «أ»" in line for line in girl[finger])
    listening = "journey-s2-p12"
    assert any(line.startswith("امْسَحِ الرَّمْزَ وَاسْمَعْ") and "ليسمع طفلكم" in line for line in boy[listening])
    assert any(line.startswith("امْسَحي الرَّمْزَ وَاسْمَعي") and "لتسمع طفلتكم" in line for line in girl[listening])
    assert "رائِعٌ يا يوسف!" in boy["journey-s2-p10"] and "رائِعَةٌ يا ليان!" in girl["journey-s2-p10"]
    boy1, girl1 = dumps["s1-interior"]
    assert "امْسَحِ الرَّمْزَ وَاسْمَعْ" in " ".join(boy1["journey-s1-p34"])
    assert "امْسَحي الرَّمْزَ وَاسْمَعي" in " ".join(girl1["journey-s1-p34"])


# ---- the audio player: one item for every child -----------------------------------------------------------

_PAIR = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")


def gendered_words() -> set[str]:
    """The words the journey prints in one gender only: every word of a `{masc/fem}` pair in the print
    layers that is not on the other side of a pair too («اسمع», «اسمعي», «بطلك»…)."""
    masc: set[str] = set()
    fem: set[str] = set()
    for layer in sorted((ROOT / "content/journey").glob("stage-*.yaml")):
        for a, b in _PAIR.findall(layer.read_text(encoding="utf-8")):
            if a != b:
                masc |= {bare(w).strip("،.؟!:") for w in a.split()}
                fem |= {bare(w).strip("،.؟!:") for w in b.split()}
    return masc ^ fem


def test_the_audio_players_words_are_the_same_for_every_child() -> None:
    words = gendered_words()
    assert {"اسمع", "اسمعي", "لون", "لوني"} <= {w.replace("ّ", "") for w in words}
    catalog = yaml.safe_load((ROOT / AUDIO.relative_to(ROOT)).read_text(encoding="utf-8"))
    for item in catalog["items"]:
        for field in ("title", "say"):
            said = {bare(w).strip("،.؟!:'\"") for w in str(item[field]).split()}
            assert not said & words, f"{item['key']} {field}: {item[field]}"
    titles = {item["key"]: item["title"] for item in catalog["items"]}
    assert titles["journey:s1:p32"] == "أَسْمَعُ الكَلِمَةَ"


# ---- the family book: the child and the grown-ups -----------------------------------------------------


def test_the_family_book_speaks_of_the_child_in_their_gender(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    boy, girl = dumps["family-interior"]
    assert "هَذا أَنا!" in boy["family-p5"] and "هَذِهِ أَنا!" in girl["family-p5"]
    assert "هَذا أَنا الآنَ!" in boy["family-p111"] and "هَذِهِ أَنا الآنَ!" in girl["family-p111"]
    # the chef adventure: «الطَّبّاخُ الصَّغيرُ» / «الطَّبّاخَةُ الصَّغيرَةُ», the same word as the stamp
    # («طَبّاخٌ صَغيرٌ» / «طَبّاخَةٌ صَغيرَةٌ»); never «الشّيف», which has no feminine
    assert "الطَّبّاخَةُ الصَّغيرَةُ" in girl["family-p24"] and "الطَّبّاخُ الصَّغيرُ" in boy["family-p24"]
    assert not any(
        "شّيف" in line or "شَّيْف" in line for d in (boy, girl) for lines in d.values() for line in lines
    )
    # a boy's past tense carries its fatha (never read as «اخترتُ», I chose): «اخترتَه»، «قلتَ»
    assert any("لماذا اخترتَه؟" in line for line in boy["family-p20"])
    assert any("«جميل أنكَ قلتَ شكرًا!»" in line for line in boy["family-p21"])
    assert any("«جميل أنكِ قلتِ شكرًا!»" in line for line in girl["family-p21"])
    assert any("«يبدو أنكِ حزنتِ»" in line for line in girl["family-p66"])


def test_role_play_lines_fit_any_seller(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    """The buyer speaks to the seller, the child first, then a grown-up of either gender: polite plural."""
    for book in dumps["family-interior"]:
        lines = book["family-p21"]
        assert "أُريدُ تُفّاحَتَيْنِ مِنْ فَضْلِكُمْ." in lines and "هَلْ عِنْدَكُمْ مَوْزٌ؟" in lines
        assert not any("فَضْلِكَ" in line or "عِنْدَكَ" in line for line in lines)


def test_a_preview_names_the_grown_up_its_page_names(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    """The opener lists «مُقابَلَةٌ مَعَ …» with the person the interview page interviews, and the page asks the
    child to draw «الضَّيْفَ» or «الضَّيْفَةَ» as that person is a man or a woman."""
    for book, guest, noun in zip(
        dumps["family-interior"], ("ماما", "بابا"), ("الضَّيْفَةَ", "الضَّيْفَ"), strict=True
    ):
        assert f"مُقابَلَةٌ مَعَ {guest}" in book["family-p78"]
        assert f"مُقابَلَةٌ مَعَ {guest}" in book["family-p81"]
        assert any(line.endswith(noun) for line in book["family-p81"]), book["family-p81"]


def test_the_play_money_is_counted_in_qamarat(dumps: dict[str, tuple[Dump, Dump]]) -> None:
    """«قَمْرَة» is a noun: its plural opens the middle letter, «ثَلاثُ قَمَراتٍ» (as تَمْرة → تَمَرات)."""
    for part, (boy, girl) in dumps.items():
        if part.startswith("family-"):
            text = "\n".join(line for book in (boy, girl) for lines in book.values() for line in lines)
            assert "قَمْراتٍ" not in text, part
    assert "السِّعْرُ ثَلاثُ قَمَراتٍ." in dumps["family-interior"][0]["family-p21"]


def test_a_family_of_six_fits_the_memory_game_tally(tmp_path: Path) -> None:
    """Seven players (the child and six members, the most a family lists) fit the tally on 21 × 28."""
    plan = load_family(ROOT / FAMILY_PLAN)
    specs, _ = plan_pages(plan, [96], {})
    book = family_spec(tuple(specs), BOY, FAMILY["m"], "21x28")
    pages = build_pages(book, ASSETS)
    assert len(pages[0].built.data["players"]) == 7
    html = book_html(book, pages, ASSETS)
    asyncio.run(print_pdf(html, tmp_path / "p96.html", tmp_path / "p96.pdf", book.geometry))  # raises if not
