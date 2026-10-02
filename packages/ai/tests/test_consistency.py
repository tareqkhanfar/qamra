"""Addendum 11 §2 and §4: the style bible (scene groups, one hijab), the companion's and side characters'
sheets, the cover plate and photo, the cover's own model, text completeness and the new QA checks. All
offline: fake image + text providers, content files in a temporary folder."""

from pathlib import Path

import pytest
from tests_helpers import png

from qamra_ai import prompts
from qamra_ai.config import Settings
from qamra_ai.cost import fal_cost
from qamra_ai.errors import InvalidOutput
from qamra_ai.image import make_cover_image_provider
from qamra_ai.image.base import ImageRequest
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.image.fal import FalImageProvider
from qamra_ai.image.fallback import FallbackImageProvider
from qamra_ai.pipeline.bible import build_bible, cover_plates
from qamra_ai.pipeline.book import BookInputs, choose_outfits, default_companion, run_book
from qamra_ai.pipeline.fakes import good_page_qa
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child, CompanionSpec, PageQA, StoryOut, StoryPageOut
from qamra_ai.pipeline.pages import BookContext, page_request, prepare_book, qa_request
from qamra_ai.pipeline.plates import DirPlateStore
from qamra_ai.pipeline.qa import evaluate
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import base_pages, missing_text, validate_story
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import CONTENT_DIR, Theme, load_style, load_theme, theme_problems
from qamra_ai.text.base import ImagePart

GIRL = Child(name="ليان", gender="f", age=5, hijab=True)
BOY = Child(name="يوسف", gender="m", age=5)
THEMES_WITH_CAST = ("graduation", "first-day", "new-sibling")


def _ctx(theme: Theme, child: Child = GIRL, *, style: str = "watercolor", **kw: object) -> BookContext:
    return BookContext(
        child=child,
        lang="ar",
        theme=theme,
        style=load_style(style),
        house=house_style(),
        plan=plan_book(theme, "ar", companion_page=False),
        character_sheet=png("tan"),
        outfits={},
        seed=kw.pop("seed", 1),  # type: ignore[arg-type]
        companion=default_companion(theme, "ar"),
        **kw,  # type: ignore[arg-type]
    )


def _offline() -> Runtime:
    """Prompt building only: no text calls."""
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    return Runtime(settings=settings, text=None, image=FakeImageProvider())  # type: ignore[arg-type]


def _labels(req: ImageRequest) -> list[str]:
    return [r.label for r in req.refs]


def _content(tmp: Path, files: dict[str, bytes]) -> Path:
    for rel, data in files.items():
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return tmp


class Limited(FakeImageProvider):
    """A provider that takes only a few reference images."""

    def __init__(self, max_refs: int) -> None:
        super().__init__(long_side=64)
        self.max_refs = max_refs


# ---- the style bible ----------------------------------------------------------------------------


def test_bible_locks_one_outfit_per_scene_group_and_one_hijab() -> None:
    theme = load_theme("graduation")
    bible = build_bible(theme, GIRL, 1, style="watercolor", companion=default_companion(theme, "ar"))
    assert bible.main_group == "day" and set(bible.outfits) == {"day", "school", "sleep"}
    assert bible.hijab in ("a soft white hijab", "a soft cream hijab") and bible.hair == "hijab"
    lines = bible.outfit_lines()
    assert all(line.endswith(f"; {bible.hijab}") for line in lines.values())  # never another color
    assert "teal" in bible.outfits["school"] and "pajamas" in bible.outfits["sleep"]
    assert bible.companion and "plump crescent" in bible.companion
    assert set(bible.cast) == {"teacher", "classmates", "mom", "dad", "grandma"}
    assert choose_outfits(theme, GIRL, 1) == lines  # the legacy shape agrees with the bible
    boy = build_bible(theme, BOY, 1, style="watercolor")
    assert boy.hijab is None and boy.hair == "sheet" and "dress" not in boy.outfits["school"]
    # same seed → same options (a book started before the bible keeps its clothes)
    assert {build_bible(theme, GIRL, s, style="x").outfits["day"] for s in range(6)} == {
        o.en for o in theme.outfits["day"]
    }


def test_cover_group_pages_follow_the_cover_other_groups_their_first_page() -> None:
    ctx = _ctx(load_theme("graduation"), cover=png("navy"))
    rt = _offline()
    day = page_request(rt, ctx, 1, 1)  # graduation morning: the cover's group
    assert "the book's front cover: style, palette, outfit" in _labels(day)
    assert "must match the hero's clothing on the cover (Image 2) exactly" in day.prompt
    assert "a soft white hijab" in day.prompt or "a soft cream hijab" in day.prompt
    school = page_request(rt, ctx, 4, 1)  # a flashback in the school outfit, before its anchor exists
    assert "the book's front cover: style, palette" in _labels(school)
    assert "do not copy the cover's clothes" in school.prompt and "teal" in school.prompt
    assert "match the hero's clothing on the cover" not in school.prompt
    ctx.group_refs["school"] = (3, png("teal"))
    school = page_request(rt, ctx, 4, 1)
    assert _labels(school)[2] == "an earlier page of this book in the same outfit: outfit"
    assert "must match the hero's clothing in Image 3 exactly" in school.prompt
    anchor = page_request(rt, ctx, 3, 2)  # the anchor's own redraw never references itself
    assert not any(label.startswith("an earlier page") for label in _labels(anchor))
    # QA compares the outfit with the same references
    _, parts = qa_request(ctx, 4, png())
    brief = parts[-1]
    assert isinstance(brief, str) and "outfit reference: the hero in Image 3" in brief
    _, parts = qa_request(ctx, 1, png())
    assert "outfit reference: the hero in Image 2" in str(parts[-1])


async def test_each_group_is_anchored_by_its_first_accepted_page(
    rt: Runtime, fake_image: FakeImageProvider
) -> None:
    theme = load_theme("graduation")
    inp = BookInputs(
        child=GIRL,
        lang="ar",
        theme=theme,
        style=load_style("watercolor"),
        character_sheet=png("tan"),
        companion=default_companion(theme, "ar"),
        companion_sheet=png("gold"),
        seed=5,
    )
    run = await run_book(rt, inp, mode="final")
    assert run.status_counts() == {"ok": 18} and run.bible is not None
    steps = [r.step for r in fake_image.requests]
    first_of = {b: steps.index(f"page:{b}:a1") for b in range(1, 18)}
    school, sleep = [3, 4, 5, 6], [16, 17]  # graduation's school flashback and the evening pages
    assert all(first_of[3] < first_of[b] for b in school[1:])
    assert all(first_of[16] < first_of[b] for b in sleep[1:])
    by_step = {r.step: r for r in fake_image.requests}
    for b in (4, 5, 6, 17):
        assert "an earlier page of this book in the same outfit: outfit" in _labels(by_step[f"page:{b}:a1"])
    for b in (1, 2, 9, 11):
        assert "the book's front cover: style, palette, outfit" in _labels(by_step[f"page:{b}:a1"])


# ---- side characters ------------------------------------------------------------------------------


async def test_cast_sheets_go_with_their_pages_within_the_provider_limit(rt: Runtime, tmp_path: Path) -> None:
    content = _content(
        tmp_path,
        {
            "cast/teacher-watercolor.png": png("red"),
            "cast/classmates-watercolor.png": png("orange"),
            "themes/graduation/cast/mom-watercolor.png": png("pink"),  # a theme's own sheet
        },
    )
    ctx = _ctx(load_theme("graduation"), content_dir=content, companion_sheet=png("gold"), cover=png("navy"))
    await prepare_book(rt, ctx)
    assert set(ctx.cast_sheets) == {"teacher", "classmates", "mom"}
    req = page_request(rt, ctx, 3, 1)  # "{classmates} and {teacher}"
    assert _labels(req)[-2:] == ["THE FOUR CLASSMATES: character sheet", "THE TEACHER: character sheet"]
    assert "The four classmates (character sheet: Image 4)" in req.prompt
    assert "The teacher (character sheet: Image 5)" in req.prompt
    assert "Also in the picture: the four classmates and the teacher." in req.prompt
    assert "{" not in req.prompt
    family = page_request(rt, ctx, 10, 1)  # mother (sheet), father + grandmother (text only)
    assert (
        "THE MOTHER: character sheet" in _labels(family)
        and "The father: a man in his mid-thirties" in family.prompt
    )

    rt.image = FallbackImageProvider(Limited(max_refs=3), None)
    req = page_request(rt, ctx, 3, 1)  # the cast sheets are the first to go
    assert _labels(req) == [
        "THE HERO: character reference sheet of the child (likeness)",
        "the book's front cover: style, palette",
        "THE COMPANION: character sheet",
    ]
    assert "The teacher: a kind woman in her early thirties" in req.prompt  # the locked text stays


def test_cast_is_the_same_in_every_theme_and_every_member_is_used() -> None:
    seen: dict[str, tuple[str, str]] = {}
    for slug in THEMES_WITH_CAST:
        theme = load_theme(slug)
        bible = build_bible(theme, BOY, 1, style="x")
        used = {c for s in [theme.cover, *theme.pages] if s is not None for c in bible.cast_in(s.others)}
        assert {m.id for m in theme.cast} == used, slug
        for m in theme.cast:
            assert seen.setdefault(m.id, (m.role, m.description_en)) == (m.role, m.description_en), (
                slug,
                m.id,
            )
    qamour = {load_theme(s).default_companion.description_en for s in (*THEMES_WITH_CAST, "custom")}  # type: ignore[union-attr]
    assert len(qamour) == 1 and "plump crescent" in qamour.pop()


def test_theme_problems_name_unknown_cast_and_missing_text() -> None:
    data = load_theme("graduation").model_dump(mode="json")
    data["pages"][4]["others"] = "{nobody} and {teacher}"
    data["pages"][1]["text_ar"] = ""
    data["pages"][2]["wordless"] = True
    data["catalog"]["status"] = "coming_soon"  # skip the load-time validator; check the list directly
    problems = theme_problems(Theme.model_validate(data))
    assert "unknown cast member {nobody} in others" in problems
    assert any(p.startswith("page 2: no text") for p in problems)
    assert "page 3: a wordless page has text" in problems
    data["pages"][1]["text_ar"] = data["pages"][1]["text_en"] = ""
    data["pages"][1]["wordless"] = True
    data["pages"][2]["wordless"] = False
    data["pages"][4]["others"] = "{teacher}"
    assert theme_problems(Theme.model_validate(data)) == []


# ---- the companion ---------------------------------------------------------------------------------


async def test_companion_sheet_comes_from_its_file(
    rt: Runtime, fake_image: FakeImageProvider, tmp_path: Path
) -> None:
    shared = _content(tmp_path / "a", {"cast/qamour-watercolor.png": png("gold")})
    ctx = _ctx(load_theme("graduation"), content_dir=shared)
    await prepare_book(rt, ctx)
    assert ctx.companion_sheet == png("gold") and fake_image.requests == []
    own = _content(
        tmp_path / "b",
        {
            "cast/qamour-watercolor.png": png("gold"),
            "themes/graduation/cast/companion-watercolor.png": png("white"),
        },
    )
    ctx = _ctx(load_theme("graduation"), content_dir=own)
    await prepare_book(rt, ctx)
    assert ctx.companion_sheet == png("white")  # the theme's own sheet first


async def test_companion_sheet_is_drawn_once_from_its_locked_description(
    rt: Runtime, fake_image: FakeImageProvider, tmp_path: Path
) -> None:
    store = DirPlateStore(tmp_path / "store")
    for slug in ("graduation", "first-day"):  # the same «قمّور» design: one sheet for both themes
        ctx = _ctx(load_theme(slug), content_dir=tmp_path / "empty", plates=store)
        await prepare_book(rt, ctx)
        assert ctx.companion_sheet is not None
    sheets = [r for r in fake_image.requests if r.step == "companion:sheet"]
    assert len(sheets) == 1 and sheets[0].refs == [] and "plump crescent" in sheets[0].prompt
    assert "قَمّور" not in sheets[0].prompt and "Qamour" not in sheets[0].prompt  # no names in pictures
    # a drawing companion has its own sheet; pages without the companion need none
    ctx = _ctx(load_theme("graduation"), content_dir=tmp_path / "empty")
    ctx.companion = CompanionSpec(name="بوبو", description_en="a purple blob", from_drawing=True)
    await prepare_book(rt, ctx)
    ctx = _ctx(load_theme("graduation"), content_dir=tmp_path / "empty")
    await prepare_book(rt, ctx, beats=[7])  # the empty hall: no companion
    assert ctx.companion_sheet is None and len(fake_image.requests) == 1


def test_qa_compares_the_companion_with_its_sheet() -> None:
    ctx = _ctx(load_theme("graduation"), companion_sheet=png("gold"), cover=png("navy"))
    system, parts = qa_request(ctx, 1, png())
    assert "Image 3: the companion «قَمّور» character sheet (its exact design)." in parts
    assert "compare with its character sheet, Image 3" in str(parts[-1])
    assert "a crescent drawn as a round ball" in system and "plump crescent" in system


# ---- the cover ------------------------------------------------------------------------------------


async def test_cover_is_drawn_into_its_plate_with_the_photo(tmp_path: Path) -> None:
    content = _content(
        tmp_path,
        {
            "themes/first-day/plates/watercolor-2.png": png("blue"),
            "themes/first-day/plates/watercolor-1.png": png("green"),
            "themes/first-day/plates/3d-1.png": png("red"),
            "themes/first-day/plates/notes.txt": b"x",
        },
    )
    assert [p.name for p in cover_plates("first-day", "watercolor", content)] == [
        "watercolor-1.png",
        "watercolor-2.png",
    ]
    theme = load_theme("first-day")
    ctx = _ctx(theme, BOY, content_dir=content, seed=3, photo=png("pink"), cover=png("navy"))
    ctx.companion_sheet = png("gold")
    assert ctx.locks.cover_plate == "watercolor-2.png"  # seed 3 → the second plate
    rt = _offline()
    await prepare_book(rt, ctx, beats=[0])
    assert ctx.cover_plate == png("blue")
    cover = page_request(rt, ctx, 0, 1)
    assert _labels(cover)[:3] == [
        "THE HERO: character reference sheet of the child (likeness)",
        "THE COVER BACKGROUND: the finished scene to paint the hero into",
        "a photo of the hero: face likeness only",
    ]
    assert "Image 2 is this cover's finished background" in cover.prompt
    assert "Image 3 is a photo of the hero" in cover.prompt and "TOP 30% calm and empty" in cover.prompt
    page = page_request(rt, ctx, 2, 1)
    assert not any("photo" in label or "BACKGROUND" in label for label in _labels(page))
    # the photo never goes to QA (Anthropic): the character sheet, the companion's sheet and the cover itself
    _, parts = qa_request(ctx, 0, png())
    assert sum(isinstance(p, ImagePart) for p in parts) == 3
    assert not any("photo" in p for p in parts if isinstance(p, str))


async def test_the_cover_can_use_its_own_model(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    covers = FakeImageProvider(long_side=64)
    rt.cover_image = FallbackImageProvider(covers, None)
    book_inputs.companion_sheet = png("gold")
    await run_book(rt, book_inputs, mode="preview", beats=[0, 1])
    assert [r.step for r in covers.requests] == ["cover:a1"]
    assert [r.step for r in fake_image.requests] == ["page:1:a1"]


def test_cover_model_settings_and_prices() -> None:
    base = Settings(_env_file=None, fal_key="k", image_provider="fal")  # type: ignore[call-arg, arg-type]
    assert make_cover_image_provider(base) is None  # default: the page model draws the cover
    same = base.model_copy(update={"cover_image_model": base.fal_image_model})
    assert make_cover_image_provider(same) is None
    pro = make_cover_image_provider(base.model_copy(update={"cover_image_model": "fal-ai/nano-banana-pro"}))
    assert pro is not None and pro.model == "fal-ai/nano-banana-pro" and pro.fallback is not None
    assert pro.fallback.model == "fal-ai/nano-banana-2" and pro.max_refs == 14
    offline = base.model_copy(
        update={"image_provider": "fake", "cover_image_model": "fal-ai/nano-banana-pro"}
    )
    assert make_cover_image_provider(offline) is None
    endpoint, args, _ = FalImageProvider(None, "fal-ai/nano-banana-pro", client=object()).build(  # type: ignore[arg-type]
        ImageRequest(step="cover:a1", prompt="p", refs=[], resolution="0.5K")
    )
    assert endpoint == "fal-ai/nano-banana-pro" and args["resolution"] == "1K"  # Pro has no 0.5K tier
    assert fal_cost("fal-ai/nano-banana-pro/edit", resolution="1K") == pytest.approx(0.15)
    assert fal_cost("fal-ai/nano-banana-pro/edit", resolution="4K") == pytest.approx(0.30)


# ---- text completeness -------------------------------------------------------------------------------


def _story(n: int, empty: int | None = None) -> StoryOut:
    pages = [StoryPageOut(index=i, text="" if i == empty else f"نصّ {i}") for i in range(1, n + 1)]
    return StoryOut(title="t", dedication="d", pages=pages, parents_questions=["a", "b"])


def test_every_story_page_needs_text_unless_wordless() -> None:
    with pytest.raises(InvalidOutput, match=r"without text: \[4\]"):
        validate_story(_story(17, empty=4), 17)
    story = validate_story(_story(17), 17, {4})
    assert story.pages[3].text == ""  # a wordless page stays silent
    theme = load_theme("first-day")
    assert missing_text(theme, _story(17, empty=4)) == [4] and missing_text(theme, _story(17)) == []
    data = theme.model_dump(mode="json")
    data["pages"][3].update(wordless=True, text_ar="", text_en="")
    silent = Theme.model_validate(data)
    assert missing_text(silent, _story(17, empty=4)) == []
    assert base_pages(silent, BOY, "ar", "قمّور")[3]["wordless"] is True


async def test_a_book_with_a_silent_page_fails(rt: Runtime, book_inputs: BookInputs) -> None:
    book_inputs.story = _story(17, empty=9)
    with pytest.raises(InvalidOutput, match="without text"):
        await run_book(rt, book_inputs, mode="preview")


# ---- QA ------------------------------------------------------------------------------------------------


def _qa(**change: object) -> PageQA:
    return good_page_qa().model_copy(update=change)


@pytest.mark.parametrize(
    ("change", "flag"),
    [
        ({"hijab_ok": False}, "hijab"),
        ({"outfit_ok": False}, "outfit"),
        ({"companion_ok": False}, "companion"),
        ({"cropped": ["hero"]}, "crop"),
        ({"cropped": ["The hero's left hand"]}, "crop"),
    ],
)
def test_consistency_misses_are_redrawn(change: dict[str, object], flag: str) -> None:
    v = evaluate(_qa(**change), expect_hero=True, expect_companion=True, threshold=0.5)
    assert not v.passed and flag in v.flags and v.lock_misses == 1 and v.hard == 0


def test_soft_crop_and_plates() -> None:
    v = evaluate(_qa(cropped=["the teacher"]), expect_hero=True, expect_companion=True, threshold=0.75)
    assert v.passed and v.flags == ("crop_other",) and v.score == pytest.approx(0.89)
    plate = _qa(hero_count=0, hijab_ok=False, outfit_ok=False)
    assert evaluate(plate, expect_hero=False, expect_companion=False, threshold=0.75).passed


async def test_a_redraw_is_told_what_failed(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    answers = [
        good_page_qa(),
        _qa(text_in_image=True),
        _qa(hijab_ok=False, cropped=["hero"]),
        _qa(outfit_ok=False),
    ]
    rt.text.responders["PageQA"] = lambda *_: answers.pop(0) if answers else good_page_qa()  # type: ignore[attr-defined]
    book_inputs.companion_sheet = png("gold")
    run = await run_book(rt, book_inputs, mode="final", beats=[0, 1])
    page = run.pages[1]
    assert page.status == "needs_review" and page.redraws == 2
    assert page.qa is not None and not page.qa.text_in_image  # a broken lock ranks above a hard fail
    prompts_ = [r.prompt for r in fake_image.requests if r.step.startswith("page:1")]
    assert "THE LAST ATTEMPT FAILED REVIEW" not in prompts_[0]
    assert "No letters, numbers, writing or signs anywhere" in prompts_[1]
    assert "exactly the one in the OUTFIT section" in prompts_[2] and "head, hands and feet" in prompts_[2]


def test_qa_prompt_v5_asks_for_the_new_checks() -> None:
    ctx = _ctx(load_theme("graduation"), cover=png("navy"))
    system, parts = qa_request(ctx, 10, png())
    for field in ("cropped:", "hijab_ok:", "outfit_ok:", "text_space_ok:", "companion_ok:"):
        assert f"- {field}" in system
    assert "busy detail" in system and "outer 5% border band" in system
    assert "- The teacher: a kind woman" in system  # the book's cast, cached with the system prompt
    brief = str(parts[-1])
    assert "Other people: the mother, the father and the grandmother in the front row" in brief
    assert "- The mother: a woman in her early thirties" in brief
    assert "Hero's head covering: a soft" in brief
    assert set(PageQA.model_fields) >= {"cropped", "hijab_ok"}
    assert prompts.render("page_qa_brief", version=1, **_brief_v1())  # older books' prompts still render


def _brief_v1() -> dict[str, object]:
    return {
        "page_label": "page 2",
        "scene": "s",
        "expect_hero": True,
        "others": None,
        "companion": None,
        "outfit": "o",
        "text_area_label": "top",
    }


def test_real_content_has_no_sheet_files_yet_and_pages_still_draw() -> None:
    """Until Tareq's images land, books draw from the locked texts (no missing-file errors)."""
    ctx = _ctx(load_theme("graduation"), content_dir=CONTENT_DIR)
    rt = _offline()
    req = page_request(rt, ctx, 3, 1)
    assert "The teacher" in req.prompt and "a kind woman in her early thirties" in req.prompt
