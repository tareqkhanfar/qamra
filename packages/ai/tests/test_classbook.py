"""«كتاب الصف»: the class template, the fair plan (every child ≥ N times, never twice on a page, capped per
picture) and the multi-child pictures with their vision check, on the offline providers."""

import pytest
from tests_helpers import png

from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.classbook import (
    ChildCheck,
    Kid,
    SceneQA,
    assign,
    build_plan,
    class_template_slugs,
    coverage,
    draw_picture,
    install_fakes,
    join_names,
    load_class_template,
    picture_request,
    plan_scenes,
    quotas,
    refs_per_picture,
)
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.text.base import UserPart


def test_the_graduation_template_loads_and_names_the_children() -> None:
    assert "graduation" in class_template_slugs()
    t = load_class_template("graduation")
    text = t.page_text("arrive", "ar", ["يوسف", "جنى", "ليان"], "صف الفراشات")
    assert "يوسف وجنى وليان" in text and "{" not in text
    assert "أَطْفالُ صف الفراشات" in t.page_text("arrive", "ar", [], "صف الفراشات")  # Classic: no names
    assert t.page_text("caps#2", "en", ["Yusuf"], "Stars").endswith("Yusuf!")  # a repeat reuses the scene
    assert "نَجْمَةٌ" in t.portrait_line("ar", 0, "f", "جنى") and "نَجْمٌ" in t.portrait_line("ar", 0, "m", "آدم")
    assert join_names(["Yusuf", "Jana", "Layan"], "en") == "Yusuf, Jana and Layan"


def test_refs_per_picture_reads_the_setting_per_provider() -> None:
    assert refs_per_picture("fal:3, gemini:4, openai:2", "gemini") == 4
    assert refs_per_picture("fal:3", "openai") == 3  # unlisted → 3
    assert refs_per_picture("fal:9", "fal") == 6  # never more than 6 references


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 13, 18, 25, 30])
@pytest.mark.parametrize("each", [1, 2, 3])
@pytest.mark.parametrize("cap", [2, 3, 4])
def test_every_child_appears_exactly_n_times_never_twice_on_a_page(n: int, each: int, cap: int) -> None:
    t = load_class_template("graduation")
    kids = [f"k{i}" for i in range(n)]
    plan = build_plan(t, kids, min_each=each, cap=cap, line="magic", seed=n * 31 + each)
    counts = coverage([p.children for p in plan], kids)
    assert set(counts.values()) == {each}, counts
    for page in plan:
        assert len(page.children) <= page.slots <= cap
        assert len(set(page.children)) == len(page.children)
    assert [p.index for p in plan] == list(range(1, len(plan) + 1))
    # every core scene is in the book, in the template's order
    core = [s.key for s in t.scenes if not s.extra]
    keys = [p.key for p in plan]
    assert [k for k in keys if k in core] == core


def test_a_class_of_30_fits_with_three_children_per_picture() -> None:
    t = load_class_template("graduation")
    kids = [f"k{i}" for i in range(30)]
    plan = build_plan(t, kids, min_each=2, cap=3, line="magic", seed=1)
    assert len(plan) == 20 and all(len(p.children) == 3 for p in plan)
    # appearances are spread: a child's two pages are never neighbours
    for kid in kids:
        where = [p.index for p in plan if kid in p.children]
        assert where[1] - where[0] > 1, (kid, where)


def test_quotas_fill_pages_evenly_and_respect_places() -> None:
    assert quotas([3, 3, 3], 7) in ([3, 2, 2], [2, 3, 2], [2, 2, 3])
    assert quotas([1, 3, 3], 7) == [1, 3, 3]
    assert sum(quotas([3] * 13, 16)) == 16 and max(quotas([3] * 13, 16)) == 2


def test_the_plan_is_reproducible_and_classic_has_no_named_children() -> None:
    t = load_class_template("graduation")
    kids = [f"k{i}" for i in range(12)]
    assert build_plan(t, kids, min_each=2, cap=3, line="magic", seed=5) == build_plan(
        t, kids, min_each=2, cap=3, line="magic", seed=5
    )
    classic = build_plan(t, kids, min_each=2, cap=3, line="classic", seed=5)
    assert classic and all(not p.children and p.slots == 0 for p in classic)
    assert len(classic) == len(plan_scenes(t, 12, 2, 3, "classic"))
    assert assign([], [3, 3], 2, 1) == [[], []]


def _kids(n: int) -> list[Kid]:
    return [Kid(f"k{i}", f"n{i}", "f" if i % 2 else "m", 5, i == 1, False, png("tan")) for i in range(n)]


async def test_a_class_picture_sends_every_child_as_a_reference_and_passes(rt: Runtime) -> None:
    install_fakes(rt)
    t = load_class_template("graduation")
    kids = _kids(3)

    def make(n: int):  # type: ignore[no-untyped-def]
        return picture_request(
            t,
            t.scene("paint"),
            kids,
            "watercolor",
            kind="page",
            step=f"class:3:a{n}",
            seed=n,
            resolution="1K",
        )

    req = make(1)
    assert len(req.refs) == 3 and "CHILD 3 is the child in Image 3" in req.prompt
    assert "wearing a soft hijab" in req.prompt and "TOP 30%" in req.prompt
    pic = await draw_picture(rt, make, kids, "paint", label="class:3")
    assert pic.status == "ok" and pic.image is not None and not pic.unrecognized
    assert len(pic.attempts) == 1


async def test_an_unrecognized_child_is_redrawn_then_flagged(
    rt: Runtime, fake_image: FakeImageProvider
) -> None:
    install_fakes(rt)

    def missing_second(step: str, system: str, user: list[UserPart]) -> SceneQA:
        return SceneQA(
            children=[ChildCheck(ref=1, found=True, likeness=9), ChildCheck(ref=2, found=False, likeness=0)],
            people_count_ok=False,
            anatomy_ok=True,
            text_in_image=False,
            style_ok=True,
            safe=True,
        )

    rt.text.responders["SceneQA"] = missing_second  # type: ignore[attr-defined]
    t = load_class_template("graduation")
    kids = _kids(2)
    pic = await draw_picture(
        rt,
        lambda n: picture_request(
            t, t.scene("yard"), kids, "watercolor", kind="page", step=f"class:6:a{n}", seed=n, resolution="1K"
        ),
        kids,
        "yard",
        label="class:6",
    )
    assert pic.status == "needs_review" and pic.unrecognized == ["k1"] and "face" in pic.flags
    assert len(pic.attempts) == 1 + rt.settings.page_max_regenerations
    assert len(fake_image.requests) == len(pic.attempts)
