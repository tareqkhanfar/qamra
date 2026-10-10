"""«تحقق من التذكير والتأنيث»: the deterministic gender check of a story's words (`pipeline.gender_check`),
the gender rules in the story prompts, and every theme's texts read for a boy and a girl.

The check must stay quiet on correct words (every theme rendered for both genders, and the 7 example books
the model wrote), find the slips planted in them, and never block a book: a story with a slip is returned
with its hints, and the book goes to the staff text review.
"""

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from qamra_ai import prompts
from qamra_ai.pipeline.classbook import class_template_slugs, load_class_template
from qamra_ai.pipeline.classic import classic_story
from qamra_ai.pipeline.gender_check import check_texts, gender_issues, lexicon, review_notes, theme_pairs
from qamra_ai.pipeline.models import Child, Gender, SafetyVerdict, StoryOut, StoryPageOut
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import write_story
from qamra_ai.pipeline.theme import CONTENT_DIR, Theme, fill_title, load_theme, render_template
from qamra_ai.pipeline.vowelize import (
    DEDICATION_AR,
    TEXT_FIXES,
    VowelizedTexts,
    checked,
    corrected_cache,
    corrected_definition,
    gender_marks_kept,
    source_hash,
    sources,
)
from qamra_pdf.strings import STRINGS

EXAMPLES = json.loads(
    (Path(__file__).parent / "fixtures/gender/example_books.json").read_text(encoding="utf-8")
)
THEMES = sorted(p.name for p in (CONTENT_DIR / "themes").iterdir() if (p / "theme.yaml").is_file())
STORIES = [s for s in THEMES if load_theme(s).pages]
NAMES = {("ar", "m"): "يوسف", ("ar", "f"): "ليان", ("en", "m"): "Yousef", ("en", "f"): "Layan"}
OTHER: dict[str, Gender] = {"m": "f", "f": "m"}
_LEFTOVER = re.compile(r"[{}]|\S/\S")


def _companion(theme: Theme, lang: str) -> str:
    c = theme.default_companion
    return (c.name_ar if lang == "ar" else c.name_en) if c else ""


def _rules(text: str, name: str, gender: Gender) -> list[tuple[str, str]]:
    return [(i.rule, i.word) for i in check_texts([("page:1", text)], name, gender, "ar")]


# ---- every theme, read for a boy and a girl ------------------------------------------------------


def _theme_texts(theme: Theme, lang: str, gender: Gender) -> list[str]:
    """Every story-book text of a theme for one child: what the dumps for the gender review show."""
    name, comp = NAMES[(lang, gender)], _companion(theme, lang)
    ar = lang == "ar"

    def r(t: str | None) -> str:
        return render_template(t or "", gender, name, comp)

    out = [
        fill_title(theme.title_ar if ar else theme.title_en, name, gender),
        r(theme.blurb_ar if ar else theme.blurb_en),
    ]
    out += [r(p.text_ar if ar else p.text_en) for p in theme.pages]
    if theme.for_parents:
        fp = theme.for_parents
        out += [
            r(fp.lesson_ar if ar else fp.lesson_en),
            *(r(q) for q in (fp.questions_ar if ar else fp.questions_en)),
        ]
    out.append(r(DEDICATION_AR if ar else "To {name}, our little star: we love you to the moon."))
    return out


@pytest.mark.parametrize("slug", THEMES)
@pytest.mark.parametrize("lang", ["ar", "en"])
@pytest.mark.parametrize("gender", ["m", "f"])
def test_every_theme_text_renders_whole_for_both_genders(slug: str, lang: str, gender: Gender) -> None:
    theme = load_theme(slug)
    for text in _theme_texts(theme, lang, gender):
        assert not _LEFTOVER.search(text), text  # no brace and no «حارس/حارسة» left for a child
    if theme.catalog:
        for text in (theme.catalog.name_ar, theme.catalog.tagline_ar, theme.catalog.description_ar):
            assert not _LEFTOVER.search(text), text


@pytest.mark.parametrize("slug", STORIES)
@pytest.mark.parametrize("lang", ["ar", "en"])
@pytest.mark.parametrize("gender", ["m", "f"])
def test_the_check_is_quiet_on_every_theme(slug: str, lang: str, gender: Gender) -> None:
    """The theme's own words for each gender read clean (no false alarm on the reviewed texts)."""
    theme = load_theme(slug)
    name, comp = NAMES[(lang, gender)], _companion(theme, lang)
    story = classic_story(theme, Child(name=name, gender=gender, age=5), lang, comp)  # type: ignore[arg-type]
    assert gender_issues(story, name, gender, lang, companion=comp, theme=theme) == []  # type: ignore[arg-type]


@pytest.mark.parametrize("slug", STORIES)
@pytest.mark.parametrize("gender", ["m", "f"])
def test_the_other_genders_words_are_found(slug: str, gender: Gender) -> None:
    """A whole book in the other gender's words (the worst slip) is found on most of its pages."""
    theme = load_theme(slug)
    name = NAMES[("ar", gender)]
    story = classic_story(theme, Child(name=name, gender=OTHER[gender], age=5), "ar", _companion(theme, "ar"))
    issues = gender_issues(story, name, gender, "ar", companion=_companion(theme, "ar"), theme=theme)
    pages = {i.field for i in issues if i.field.startswith("page:")}
    gendered = [p for p in theme.pages if "{" in p.text_ar.replace("{name", "").replace("{companion", "")]
    assert len(pages) >= 0.8 * len(gendered), (slug, sorted(pages))


def test_the_lexicon_knows_the_themes_verbs() -> None:
    lex = lexicon()
    assert lex.past["قال"] == ("m", False) and lex.past["قالت"] == ("f", False)
    assert lex.past["ضم"][1] and lex.impf["تراقب"][0] == "f" and lex.second["ارسمي"] == "f"
    assert len(theme_pairs()) > 150  # every one-word {m/f} pair of the themes feeds it


# ---- the rules, one by one ---------------------------------------------------------------------

FOUND = [
    ("m", "قَالَتْ يُوسُفُ: «مَرْحَبًا!»", ("verb_before_name", "قَالَتْ")),
    ("f", "ضَحِكَ لَيَانُ كَثِيرًا.", ("verb_before_name", "ضَحِكَ")),
    ("f", "لَيَانُ يَضْحَكُ فِي السَّاحَةِ.", ("verb_after_name", "يَضْحَكُ")),
    ("m", "وَضَمَّتْ مَامَا يُوسُفَ، ثُمَّ ضَمَّتْهُ سِتِّي. فَرِحَتْ يُوسُفُ.", ("verb_before_name", "فَرِحَتْ")),
    ("m", "قَالَتْ مَامَا: «أَحْسَنْتِ يَا يُوسُفُ!»", ("addressed", "أَحْسَنْتِ")),
    ("m", "قَالَتْ مَامَا لِيُوسُفَ: «أَنَا مَعَكِ دَائِمًا».", ("addressed", "مَعَكِ")),
    ("f", "قَالَ بَابَا: «لَا تَخَفْ يَا لَيَانُ!»", ("addressed", "تَخَفْ")),
    ("f", "قَالَ بَابَا: «يَا لَيَانُ، أَنْتَ شُجَاعٌ!»", ("addressed", "أَنْتَ")),
    ("m", "قَالَ بَابَا: «تَعَالَيْ يَا يُوسُفُ، هَلْ تُحِبِّينَ الْقَمَرَ؟»", ("addressed", "تُحِبِّينَ")),
    ("f", "قَالَتْ سِتِّي: «الرَّوْضَةُ تَنْتَظِرُكَ يَا بَطَلُ!»", ("epithet", "يَا بَطَلُ")),
    ("m", "قالت ماما ليوسف: «تعالي يا حبيبتي»", ("addressed", "تعالي")),
]


@pytest.mark.parametrize(("gender", "text", "hit"), FOUND)
def test_a_slip_is_found(gender: Gender, text: str, hit: tuple[str, str]) -> None:
    assert hit in _rules(text, "يوسف" if gender == "m" else "ليان", gender)


QUIET = [
    ("m", "وَضَمَّتْ مَامَا يُوسُفَ."),  # mama hugged him
    ("m", "وَضَمَّتْ يُوسُفَ بِحُبٍّ."),  # an object, unmarked as the subject
    ("f", "شَعْرُ لَيَانَ طَوِيلٌ."),  # her hair, not «he felt»
    ("f", "شعر ليان طويل."),  # unvowelized: it could be either, so it is left alone
    ("f", "يَا لَيَانُ، ضَحِكَ الْجَمِيعُ هُنَاكَ وَأَمْسَكَ قَمّور السَّمَكَ."),
    ("f", "قَالَتْ مَامَا: «مَعَكِ دَائِمًا يَا لَيَانُ»، وَقَالَ قَمّور: «وَأَنَا مَعَكِ!»"),
    ("m", "قَالَ يُوسُفُ: «شُكْرًا يَا مَامَا، أُحِبُّكِ!»"),  # the hero speaks to mama
    ("f", "قالت ليان: «معك يا بابا»"),  # no mark: right for both
    ("m", "يَوْمُ تَخَرُّجِ يُوسُفَ"),  # «تخرّج», graduation, not «she goes out»
    ("f", "قَالَتِ الْمُعَلِّمَةُ لِلَيَانَ: «أَنْتِ رَائِعَةٌ!» وَصَفَّقَ قَمّور."),
]


@pytest.mark.parametrize(("gender", "text"), QUIET)
def test_right_words_are_left_alone(gender: Gender, text: str) -> None:
    assert _rules(text, "يوسف" if gender == "m" else "ليان", gender) == []


def test_a_name_of_the_five_nouns_is_found_in_its_cases() -> None:
    assert ("verb_before_name", "قَالَتْ") in _rules("قَالَتْ أَبُو بَكْرٍ: «هَيّا!»", "أبو بكر", "m")
    assert ("addressed", "أَنْتِ") in _rules("قَالَ بَابَا: «يَا أَبَا بَكْرٍ، أَنْتِ بَطَلٌ!»", "أبو بكر", "m")


def test_english_pronouns() -> None:
    def en(text: str, gender: Gender) -> list[str]:
        return [
            i.word
            for i in check_texts(
                [("page:1", text)], "Layan" if gender == "f" else "Yousef", gender, "en", companion="Qamour"
            )
        ]

    assert en("Yousef hugged herself tight.", "m") == ["herself"]
    assert en("Layan put on his new shoes.", "f") == ["his"]
    assert en("Mama smiled. Yousef hugged her.", "m") == []  # mama is the «her»
    assert en("Layan laughed, and Qamour waved his little arms.", "f") == []  # the companion is a «he»


# ---- the model's real stories ------------------------------------------------------------------


def _example(book: dict[str, Any]) -> tuple[StoryOut, Gender, Theme]:
    story = StoryOut(
        title=book["title"],
        dedication=book["dedication"],
        pages=[StoryPageOut(index=p["index"], text=p["text"]) for p in book["pages"]],
    )
    return story, "m" if book["variant"] == "boy" else "f", load_theme(book["theme"])


@pytest.mark.parametrize("book", EXAMPLES, ids=[f"{b['theme']}-{b['variant']}" for b in EXAMPLES])
def test_the_example_books_read_clean(book: dict[str, Any]) -> None:
    story, gender, theme = _example(book)
    assert gender_issues(story, book["child_name"], gender, "ar", companion="قَمُّور", theme=theme) == []


SLIPS = [  # (page, the right words, the slip planted in their place)
    (2, "وَحَمَلَ حَقِيبَتَهُ", "وَحَمَلَ حَقِيبَتَهَا"),
    (6, "لَا تَخَفْ، أَنَا مَعَكَ", "لَا تَخَافِي، أَنَا مَعَكِ"),
    (8, "فَتَحَ آدَمُ", "فَتَحَتْ آدَمُ"),
    (14, "شُكْرًا يَا بَطَلُ", "شُكْرًا يَا بَطَلَةُ"),
    (16, "أَنْتَ شُجَاعٌ", "أَنْتِ شُجَاعَةٌ"),
]


@pytest.mark.parametrize(("index", "right", "slip"), SLIPS)
def test_a_slip_planted_in_a_real_book_is_found(index: int, right: str, slip: str) -> None:
    book = next(b for b in EXAMPLES if b["theme"] == "first-day" and b["variant"] == "boy")
    story, gender, theme = _example(book)
    page = story.pages[index - 1]
    assert right in page.text
    pages = [
        p.model_copy(update={"text": p.text.replace(right, slip)}) if p.index == index else p
        for p in story.pages
    ]
    issues = gender_issues(story.model_copy(update={"pages": pages}), "آدم", gender, "ar", theme=theme)
    assert {i.field for i in issues} == {f"page:{index}"}, issues


# ---- the pipeline flags, never blocks ------------------------------------------------------------


async def test_a_misgendered_story_is_returned_with_its_hints(
    rt: Runtime, theme: Theme, child: Child
) -> None:
    """The model slipped on page 6 and the safety review noticed: the story is not blocked; both hints go to
    the book's text review."""
    from qamra_ai.pipeline.fakes import fake_story

    def slipped(step: str, system: str, user: list[object]) -> StoryOut:
        out = fake_story(step, system, user)  # type: ignore[arg-type]
        assert isinstance(out, StoryOut)
        pages = [
            p.model_copy(update={"text": p.text.replace("لَا تَخَافِي", "لَا تَخَفْ")}) if p.index == 6 else p
            for p in out.pages
        ]
        return out.model_copy(update={"pages": pages})

    rt.text.responders["StoryOut"] = slipped  # type: ignore[attr-defined]
    rt.text.responders["SafetyVerdict"] = lambda *_: SafetyVerdict(  # type: ignore[attr-defined]
        safe=True, reasons=[], gender_issues=["page 6: لَا تَخَفْ → لَا تَخَافِي"]
    )
    story = await write_story(rt, theme, child, "ar", None)
    found = {(i.field, i.rule) for i in story.gender_issues}
    assert found == {("page:6", "theme_word"), ("review", "text_review")}  # «تَخَفْ» is the base text's boy word
    system = rt.text.calls[0]["system"][0].text  # type: ignore[attr-defined]
    assert "Gender agreement is the most important rule" in system
    user = rt.text.calls[0]["user"][0]  # type: ignore[attr-defined]
    assert "gender check for this girl" in user and "«لا تَخافي»" in user
    safety = rt.text.calls[1]["system"]  # type: ignore[attr-defined]
    assert "gender_issues" in safety and "never set safe=false for it" in safety


async def test_a_clean_story_has_no_hints(rt: Runtime, theme: Theme, child: Child) -> None:
    story = await write_story(rt, theme, child, "ar", None)
    assert story.gender_issues == []


def test_review_notes_become_hints() -> None:
    notes = review_notes(["page 3: قالت → قال", " "])
    assert [(n.field, n.rule) for n in notes] == [("review", "text_review")]


@pytest.mark.parametrize("gender", ["m", "f"])
def test_the_prompts_spell_out_the_gender(gender: Gender) -> None:
    base = {"brand_name_en": "Qamra", "brand_name_ar": "قمرة", "theme_bible": "Beats: 1. x"}
    system = prompts.render("story_adapt", version=3, lang="ar", **base)
    assert system == prompts.render("story_adapt", version=3, lang="ar", **base)  # cacheable: no child data
    assert "The companion is always masculine" in system and "the dual" in system
    custom = prompts.render("story_custom", version=2, brand_name_en="Qamra", brand_name_ar="قمرة", lang="ar")
    assert "family's own word for them" in custom and "The companion is always masculine" in custom
    en = prompts.render("story_adapt", version=3, lang="en", **base)
    assert 'never "they" for the hero' in en
    vowelize = prompts.render("classic_vowelize", version=2, gender=gender)
    assert ("«مَعَكِ»" in vowelize) == (gender == "f")


# ---- Classic: the vowelization keeps the gender, and the deploy patches the cache ------------------


def test_a_flipped_gender_vowel_keeps_the_source() -> None:
    assert not gender_marks_kept("«أَنَا مَعَكِ دَائِمًا!»", "«أَنَا مَعَكَ دَائِمًا!»")
    assert gender_marks_kept("«أنا معكِ»", "«أَنَا مَعَكِ»") and gender_marks_kept("معك", "مَعَكَ")
    source = sources(load_theme("first-day"), "f")
    answer = source.model_copy(deep=True)
    answer.pages[5].text = answer.pages[5].text.replace("مَعَكِ", "مَعَكَ")  # the model turned her «you» into his
    result = checked(source, answer)
    assert result.kept == ["page:6"] and result.texts.pages[5].text == source.pages[5].text


def _before(definition: dict[str, Any], slug: str) -> dict[str, Any]:
    """A theme definition as it was before the gender review's wording fixes."""
    fixes = [f for f in TEXT_FIXES if f.theme == slug]

    def back(node: Any) -> Any:
        if isinstance(node, str):
            for f in fixes:
                node = node.replace(f.new, f.old)
            return node
        if isinstance(node, list):
            return [back(v) for v in node]
        if isinstance(node, dict):
            return {k: back(v) for k, v in node.items()}
        return node

    return back(copy.deepcopy(definition))  # type: ignore[no-any-return]


@pytest.mark.parametrize("slug", sorted({f.theme for f in TEXT_FIXES}))
def test_the_theme_files_carry_the_wording_fixes(slug: str) -> None:
    current = load_theme(slug).model_dump(mode="json")
    old = _before(current, slug)
    assert old != current and corrected_definition(old) == current
    assert corrected_definition(current) == current  # nothing left: the next deploy does nothing


@pytest.mark.parametrize("gender", ["m", "f"])
def test_a_cached_lesson_takes_the_new_words_without_the_model(gender: Gender) -> None:
    """new-sibling's «للأهل» now reads «تُطَمْئِنُهُ/تُطَمْئِنُها الحكاية بأنّ…»: a template vowelized from the old
    words (the model added its own marks) gets the new words and a cache keyed to them."""
    current = load_theme("new-sibling").model_dump(mode="json")
    old = _before(current, "new-sibling")
    old_source = sources(Theme.model_validate(old), gender)
    model = old_source.model_copy(deep=True)
    model.lesson = model.lesson.replace("تطمئن الحكاية أنّ", "تُطَمْئِنُ الحِكايَةُ أَنَّ")
    cache = {"hash": source_hash(old_source), "gender": gender, "texts": model.model_dump(), "kept": []}
    done = corrected_cache(old, cache, gender)
    assert done is not None
    definition, fixed = done
    assert definition == current
    assert fixed["hash"] == source_hash(sources(Theme.model_validate(current), gender))  # fresh: no new call
    lesson = VowelizedTexts.model_validate(fixed["texts"]).lesson
    assert ("تُطَمْئِنُهُ الحكاية بأنّ مكانَه" if gender == "m" else "تُطَمْئِنُها الحكاية بأنّ مكانَها") in lesson
    assert "تُطَمْئِنُ الحِكايَةُ" not in lesson


# ---- the class book and the fixed PDF words --------------------------------------------------------


@pytest.mark.parametrize("slug", class_template_slugs())
def test_class_pages_name_any_group_without_agreeing_with_it(slug: str) -> None:
    """One child, two, only girls: no plural noun («الرَّسّامونَ», «الأَصْدِقاءُ») stands right before the names."""
    t = load_class_template(slug)
    for scene in t.scenes:
        before = scene.text_ar.split("{names}")[0].rstrip(" :")
        last = before.split()[-1] if before.split() else ""
        assert not re.search("(ونَ|ونَ:|ينَ|اءُ|ِيّونَ)$", last), (scene.key, last)
        for names in (["ليان"], ["ليان", "جنى"], ["يوسف", "ليان", "آدم"], []):
            assert not _LEFTOVER.search(t.page_text(scene.key, "ar", names, "صف الفراشات"))
    assert t.portrait_title("ar", "m") == "هٰذا أَنا" and t.portrait_title("ar", "f") == "هٰذِهِ أَنا"
    for i in range(len(t.portrait_lines_ar)):
        for g in ("m", "f"):
            assert not _LEFTOVER.search(t.portrait_line("ar", i, g, "ليان"))  # type: ignore[arg-type]


def test_the_book_strings_never_speak_to_a_boy_only() -> None:
    s = STRINGS["ar"]
    assert s["scan_listen"] == "امْسَحوا وَاسْمَعوا"  # the family, like «امْسَحوا الرَّمْزَ…»
    assert s["activity_title_f"].startswith("ارْسُمي") and s["ribbon_f"].endswith("الرَّائِعَةِ")
