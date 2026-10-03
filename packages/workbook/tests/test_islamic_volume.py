# ruff: noqa: E501  (page fixtures are one Arabic dict per line)
"""«قلبي يعرف الله» volumes: the page types the volumes use, the placement ↔ content matching (keys), the writers'
guide's examples, the V1 seed, the sacred-page / no-depiction checks on the new types, the print gate (sources
and the scholar's review export), and a rendered slice of V1 that passes preflight. Every wording comes from a
FAKE corpus (`fake_resolver`); no test depends on a real verse or hadith."""

import asyncio
import datetime as dt
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from qamra_workbook import islamic
from qamra_workbook import islamic_checks as checks
from qamra_workbook.pictures.islamic_backdrops import BACKDROPS, PERSON_PICTURES, compose, composed_problems
from qamra_workbook.pictures.islamic_scenes import SCENES
from qamra_workbook.render import islamic_volume as iv
from qamra_workbook.render.engine import TEMPLATES, PageProblems, build_pages
from qamra_workbook.render.islamic_content import (
    ENGINE_NAMES,
    PLAN_TYPE,
    IslamicContext,
    Missing,
    Page,
    page_spec,
    parse_page,
)
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.registry import REGISTRY
from qamra_workbook.render.spec import BookSpec, Child, product_geometry
from test_islamic_pages import ASSETS, DATE, fake_resolver

REPO = Path(__file__).resolve().parents[3]
GUIDE = REPO / "docs/islamic/content-guide.md"
NOT_PLACED = {"home-challenge", "cut-paste"}  # page types no volume lists yet


@pytest.fixture(scope="module")
def plan() -> islamic.Plan:
    return islamic.load()


@pytest.fixture(scope="module")
def resolver() -> Any:
    return fake_resolver()


def guide_entries() -> list[dict[str, Any]]:
    blocks = re.findall(r"```yaml\n(.*?)```", GUIDE.read_text(encoding="utf-8"), re.S)
    return [dict(e) for b in blocks for e in yaml.safe_load(b)]


def place_of(plan: islamic.Plan, entry: dict[str, Any]) -> tuple[str, iv.Slot] | None:
    for vid in plan.volumes:
        for slot in iv.slots(plan, vid):
            if slot.key == entry["key"] and entry["type"] in slot.fills:
                return vid, slot
    return None


def book_of(
    pages: list[Any], resolver: Any, *, mode: str = "preview", gender: str = "f", extra: Any = None
) -> Any:
    context = IslamicContext(resolver, Kit(), mode, DATE)  # type: ignore[arg-type]
    specs = tuple(page_spec(p, i, context, (extra or {}).get(p.id)) for i, p in enumerate(pages, start=1))
    child = Child("ليان" if gender == "f" else "يوسف", gender)  # type: ignore[arg-type]
    return BookSpec("islamic", "قلبي يعرف الله", child, specs, DATE, geometry=product_geometry("family"))


# ---- the vocabulary: every plan page type has content, every content type a builder and a template ------


def test_every_plan_page_type_is_filled_and_every_content_type_is_built(plan: islamic.Plan) -> None:
    assert set(plan.page_types) <= set(iv.FILLS), set(plan.page_types) - set(iv.FILLS)
    content_types = {t for fills in iv.FILLS.values() for t in fills}
    assert content_types <= set(ENGINE_NAMES)
    for ctype, engine in ENGINE_NAMES.items():
        assert engine in REGISTRY, ctype
        assert (TEMPLATES / REGISTRY[engine].template).is_file(), engine
        if ctype != "missing":  # the preview's stand-in for content not written: never in a content file
            assert ctype in plan.page_types or ctype in PLAN_TYPE, f"{ctype}: no plan type for its rules"
    for engine in ("islamic-cover-front", "islamic-cover-back"):
        assert (TEMPLATES / REGISTRY[engine].template).is_file()


def test_the_keys_follow_the_scheme_and_are_unique(plan: islamic.Plan) -> None:
    for vid in plan.volumes:
        keys = [s.key for s in iv.slots(plan, vid)]
        assert len(keys) == len(set(keys)) == len(plan.pages[vid])
        assert all(
            re.fullmatch(r"(front|end)/\d+|u-[a-z0-9-]+/(opener|parent|l\d+-\d+|closing-[12]|review-\d+)", k)
            for k in keys
        )
    v1 = {s.key: s.page for s in iv.slots(plan, "V1")}
    assert [k for k in v1 if k.startswith("front/")] == [f"front/{i}" for i in range(1, 6)]
    assert [k for k in v1 if k.startswith("end/")] == [f"end/{i}" for i in range(1, 6)]
    assert v1["u-allah/opener"].type == "unit-opener"
    assert [v1[f"u-allah/l1-{j}"].type for j in (1, 2, 3)] == ["story", "find-objects", "choose"]
    assert v1["u-allah/l1-1"].title == "مَنْ خَلَقَنِي؟"
    assert v1["u-adhkar1/l1-2"].type == "dhikr"  # the same type twice in a lesson: l1-1 and l1-2
    assert v1["u-follow/review-1"].type == "self-test" and v1["u-manners1/review-2"].type == "self-test"
    assert v1["end/1"].type == v1["end/2"].type == "assessment" and v1["end/4"].type == "certificate"
    assert iv.page_id("V1", "u-allah/l1-1") == "v1-u-allah-l1-1"


# ---- the writers' guide: one valid example of every type --------------------------------------------------


def test_the_guide_shows_every_content_type(plan: islamic.Plan) -> None:
    shown = {e["type"] for e in guide_entries()}
    aliases = {"my-day-with-allah", "quiz", "final-assessment", "unit-review", "missing"}
    assert set(ENGINE_NAMES) - aliases <= shown, set(ENGINE_NAMES) - aliases - shown


@pytest.mark.parametrize("gender", ["f", "m"])
def test_every_guide_example_is_placed_checked_and_built(
    plan: islamic.Plan, resolver: Any, gender: str
) -> None:
    rules = checks.PageRules.load()
    pages: list[Page] = []
    extra: dict[str, Any] = {}
    for n, entry in enumerate(guide_entries(), start=1):
        found = place_of(plan, entry)
        if entry["type"] in NOT_PLACED:
            raw = {**entry, "id": f"guide-{n}", "title": "مِثَالٌ", "volume": "V1"}
        else:
            assert found is not None, f"{entry['key']} ({entry['type']}) has no place in any volume"
            vid, slot = found
            content, _ = iv.match_content(plan, vid, [entry])
            assert content.problems == [], content.problems
            raw = content.raw[entry["key"]]
            extra[raw["id"]] = iv.volume_extra(plan, vid, slot)
        assert checks.errors(checks.check_page(raw, resolver, rules)) == [], raw["id"]
        assert iv.text_problems(raw["id"], raw) == []
        pages.append(parse_page(raw))
    built = build_pages(book_of(pages, resolver, gender=gender, extra=extra), ASSETS)
    assert all(not p.built.problems for p in built)
    assert all("{" not in p.title and "{" not in p.instruction for p in built)


# ---- the V1 seed --------------------------------------------------------------------------------------------


def test_every_volume_is_written_in_full_and_v1_keeps_the_samples_in_their_places(
    plan: islamic.Plan, resolver: Any
) -> None:
    """All six volumes are drafted (pending the scholar): every place has content and no check fails; V1 still
    holds the proposal's sample pages where they belong."""
    for vid in ("V1", "V2", "V3", "V4", "V5", "R"):
        content = iv.check_volume(plan, vid, resolver)
        assert content.errors == [], (vid, content.errors[:3])
        assert content.missing == [], (vid, content.missing[:3])
    v1 = iv.check_volume(plan, "V1", resolver)
    assert {"front/1", "front/4", "u-blessings/l1-2", "u-adhkar1/l1-1", "u-manners1/l1-2"} <= set(v1.pages)
    assert v1.raw["u-adhkar1/l1-1"]["id"] == "v1-u-adhkar1-l1-1"
    assert v1.raw["u-blessings/l1-3"]["unit"] == "u-blessings"


# ---- matching content to places -----------------------------------------------------------------------------


def test_matching_reports_unknown_keys_wrong_types_duplicates_and_derived_fields(plan: islamic.Plan) -> None:
    story = {"type": "story", "scene": {"backdrop": "garden"}, "lines": [{"who": "reem", "t": "مَرْحَبًا"}]}
    entries = [
        {"key": "u-allah/l9-1", **story},
        {"key": "u-allah/l1-2", **story},  # a find-objects place
        {"key": "u-allah/l1-1", **story},
        {"key": "u-allah/l1-1", **story},
        {"key": "u-allah/opener", "id": "mine", "type": "unit-opener"},
        {"key": "u-allah/parent", "unit": "u-house", "type": "parent-guide"},
        {"type": "story"},
    ]
    content, _ = iv.match_content(plan, "V1", entries)
    codes = sorted(p.code for p in content.problems)
    assert codes == ["duplicate-key", "id", "no-key", "unit", "unknown-key", "wrong-type"]
    assert list(content.pages) == ["u-allah/l1-1"]
    assert content.raw["u-allah/l1-1"]["title"] == "مَنْ خَلَقَنِي؟"  # the lesson's title by default
    titled, _ = iv.match_content(plan, "V1", [{"key": "u-allah/review-1", "type": "story"}])
    assert [p.code for p in titled.problems] == ["unknown-key"]  # u-allah has no review place


def test_default_titles_follow_the_place_and_the_childs_gender(plan: islamic.Plan) -> None:
    slots = {s.key: s for s in iv.slots(plan, "V1")}
    assert iv.default_title(plan, "V1", slots["u-allah/opener"], "unit-opener") == "اللهُ خَلَقَنِي"
    assert iv.default_title(plan, "V1", slots["u-allah/parent"], "parent-guide") == "لِلْأَهْلِ: اللهُ خَلَقَنِي"
    assert iv.default_title(plan, "V1", slots["front/1"], "front-title") == "أَعْرِفُ رَبِّي وَأُحِبُّهُ"
    test = iv.default_title(plan, "V1", slots["u-follow/review-1"], "self-test")
    assert Child("ليان", "f").personalize(test) == "اخْتَبِرِي نَفْسَكِ"


def test_word_limits_placeholders_and_the_closings_are_checked(plan: islamic.Plan, resolver: Any) -> None:
    long_line = " ".join(["كَلِمَةٌ"] * 20)
    entries = [
        {"key": "u-allah/l1-1", "type": "story", "scene": {"backdrop": "garden"}, "lines": [{"who": "reem", "t": long_line}]},
        {"key": "u-allah/l1-3", "type": "choose", "questions": [{"text": "{مَنْ؟", "choices": [{"t": "أ", "ok": True}, {"t": "ب"}], "sources": ["q-6-1"]}]},
        {"key": "u-allah/closing-1", "type": "unit-closing", "learned": ["تَعَلَّمْتُ."], "apply": "أُطَبِّقُ."},
        {"key": "u-allah/closing-2", "type": "unit-closing", "dhikr": {"source": "q-112"}},
    ]  # fmt: skip
    content = iv.check_volume(plan, "V1", resolver, entries=entries, build=False)
    codes = {(p.code, p.where) for p in content.errors}
    assert ("too-long", "u-allah/l1-1") in codes
    assert ("placeholder", "u-allah/l1-3") in codes
    assert ("closing", "u-allah/closing") in codes  # the challenge is missing from both pages


# ---- the rules on the new types -----------------------------------------------------------------------------


def _check(page: dict[str, Any], resolver: Any) -> set[str]:
    return {p.code for p in checks.errors(checks.check_page(page, resolver, checks.PageRules.load()))}


@pytest.mark.parametrize(
    "page",
    [
        {"id": "m", "type": "maze", "title": "مَتَاهَةٌ", "goal": "house", "collect": ["gift"], "sources": ["q-112"]},
        {"id": "d", "type": "draw", "title": "أَرْسُمُ", "prompt": "نَصٌّ {src:d-eat-start}"},
        {"id": "c", "type": "cut-paste", "title": "قَصٌّ", "pieces": [{"t": "أ"}, {"t": "ب"}, {"t": "ج"}], "slots": [], "dua": "d-eat-start"},
        {"id": "h", "type": "home-challenge", "title": "تَحَدٍّ", "challenge": "أُسَاعِدُ.", "quote": {"source": "h-bukhari-6094"}},
        {"id": "k", "type": "coloring", "title": "أُلَوِّنُ", "sacred_text": "none", "pics": ["sun"], "verse": {"source": "q-112"}},
    ],
)  # fmt: skip
def test_no_sacred_text_on_pages_that_are_drawn_cut_or_thrown(page: dict[str, Any], resolver: Any) -> None:
    assert "sacred-page" in _check(page, resolver)


def test_no_depiction_on_sira_and_prophet_pages_and_no_person_picture_anywhere(resolver: Any) -> None:
    sira = {
        "id": "s",
        "type": "sira-story",
        "title": "مِنَ السِّيرَةِ",
        "narrator": {"figures": ["huda"], "intro": "قَالَتْ سِتِّي."},
        "scenes": [{"backdrop": "mosque", "figures": ["reem"], "text": "نَصٌّ.", "sources": ["h-bukhari-707"]}],
        "lesson": {"text": "دَرْسٌ.", "sources": ["h-bukhari-707"]},
        "question": {
            "text": "سُؤَالٌ؟",
            "choices": [{"t": "أ", "ok": True}, {"t": "ب"}],
            "sources": ["h-bukhari-707"],
        },
    }
    assert "depiction" in _check(sira, resolver)  # tagged prophet_story by its type
    with pytest.raises(PageProblems, match="shows no person"):
        build_pages(book_of([parse_page(sira)], resolver), ASSETS)
    body = {
        **sira,
        "scenes": [{"backdrop": "home", "props": ["hand"], "text": "نَصٌّ.", "sources": ["h-bukhari-707"]}],
    }
    assert "depiction" in _check(body, resolver)  # a body part on a page that shows no person
    story = {"id": "t", "type": "story", "title": "قِصَّةٌ", "scene": {"backdrop": "home", "props": ["mother"]}, "lines": [{"who": "reem", "t": "أَهْلًا."}]}  # fmt: skip
    assert "depiction" in _check(story, resolver)  # a library person is never a prop, on any page
    maze = {
        "id": "z",
        "type": "maze",
        "title": "مَتَاهَةٌ",
        "tags": ["prophet_story"],
        "goal": "tree",
        "runner": "reader",
    }
    assert "depiction" in _check(maze, resolver)  # a prophets' maze runs with a picture, not the child
    assert "mother" in PERSON_PICTURES and "cat" not in PERSON_PICTURES
    assert composed_problems("home", ["mother"], [], people=True)
    assert composed_problems("mosque", [], ["reem"], people=False)
    assert not composed_problems("kitchen", ["cup", "isl:lantern"], ["reader", "huda"], people=True)


def test_every_backdrop_composes_with_the_cast_and_its_props() -> None:
    class Cast:
        def figure(self, who: str, x: float, y_feet: float, height: float) -> str:
            return f'<rect data-who="{who}" x="{x}" y="{y_feet - height}" width="1" height="{height}"/>'

    for name, back in BACKDROPS.items():
        props = ["cup", "isl:lantern", "book", "dates", "apple", "ball"][: len(back.spots)]
        svg = compose(name, props, ["huda", "reem", "salem", "reader"], f"t-{name}", Cast())
        assert svg.count("data-who") == 4 and svg.count("<svg") >= len(props) - 1, name
    assert not set(BACKDROPS) & set(SCENES)  # a name is a drawn scene or a backdrop, never both


# ---- the builders' own checks and answers -------------------------------------------------------------------


def test_puzzles_are_seeded_and_their_answers_listed(resolver: Any) -> None:
    pages = [
        parse_page({"id": "f", "type": "find-objects", "title": "أَبْحَثُ", "find": [{"pic": "sun", "word": "الشَّمْسُ"}, {"pic": "moon", "word": "الْقَمَرُ"}], "others": ["car", "ball", "cup"]}),
        parse_page({"id": "m", "type": "match", "title": "أَصِلُ", "pairs": [{"a": {"t": "أ"}, "b": {"pic": "sun"}}, {"a": {"t": "ب"}, "b": {"pic": "moon"}}, {"a": {"t": "ج"}, "b": {"source": "d-eat-start"}}]}),
        parse_page({"id": "z", "type": "maze", "title": "مَتَاهَةٌ", "goal": "house", "goal_word": "الْبَيْتُ", "collect": ["gift", "balloon"], "size": "large"}),
        parse_page({"id": "c", "type": "cut-paste", "title": "أَقُصُّ", "pieces": [{"pic": "seed", "t": "بَذْرَةٌ"}, {"pic": "sprout", "t": "نَبْتَةٌ"}, {"pic": "tree", "t": "شَجَرَةٌ"}]}),
    ]  # fmt: skip
    first = build_pages(book_of(pages, resolver), ASSETS)
    again = build_pages(book_of(pages, resolver), ASSETS)
    assert [str(p.built.data.get("board", "")) for p in first] == [
        str(p.built.data.get("board", "")) for p in again
    ]
    find, match, maze, cut = first
    assert find.built.answer == ["الشَّمْسُ", "الْقَمَرُ"] and "answer-ring" in str(find.built.data["rings"])
    assert len(match.built.answer or []) == 3 and match.built.answer[0].startswith("١ ← ")  # type: ignore[index]
    letters = [row["b"]["n"] for row in match.built.data["rows"]]
    assert sorted(letters) == sorted(["أ", "ب", "ج"])
    assert "#E0483A" in str(maze.built.data["svg_solved"]) and "الْبَيْتُ" in (maze.built.answer or [""])[0]
    assert [p["text"] for p in cut.built.data["pieces"]] != ["بَذْرَةٌ", "نَبْتَةٌ", "شَجَرَةٌ"]  # shuffled
    assert cut.built.answer == ["١: بَذْرَةٌ", "٢: نَبْتَةٌ", "٣: شَجَرَةٌ"]


def test_a_missing_page_shows_in_a_preview_and_stops_a_print_build(resolver: Any) -> None:
    gap = Missing(
        id="v1-x", title="مَنْ خَلَقَنِي؟", key="u-allah/l1-1", unit="u-allah", type="missing", planned="story"
    )
    built = build_pages(book_of([gap], resolver), ASSETS)
    assert built[0].spec.type == "islamic-missing" and built[0].built.data["key"] == "u-allah/l1-1"
    with pytest.raises(PageProblems, match="print build needs every page"):
        build_pages(book_of([gap], resolver, mode="print"), ASSETS)


# ---- the print gate ----------------------------------------------------------------------------------------


def approved_review(plan: islamic.Plan, volume: str, credit: str | None = None) -> iv.Review:
    units = [u["id"] for u in plan.volumes[volume]["units"]] + [f"matter-{volume.lower()}"]
    data = {
        "version": 1,
        "volumes": {
            volume: {"approved": True, "units": units, "approved_on": "2026-10-02", "credit_name": credit}
        },
        "units": {u: {"volume": volume, "status": "approved"} for u in units},
        "decisions": {},
    }
    return iv.Review(data, Path("review-status.json"))


def test_the_review_export_gates_a_print_build(plan: islamic.Plan, tmp_path: Path, monkeypatch: Any) -> None:
    units = [u["id"] for u in plan.volumes["V1"]["units"]]
    monkeypatch.delenv(iv.REVIEW_ENV, raising=False)
    monkeypatch.setattr(iv, "REVIEW_FILE", tmp_path / "none.json")
    nothing = iv.Review.load()
    assert nothing.path is None and nothing.problems("V1", units) and nothing.credit("V1") == ""
    ok = approved_review(plan, "V1", "الشيخ فلان")
    assert ok.problems("V1", units) == [] and ok.credit("V1") == "الشيخ فلان"
    assert approved_review(plan, "V1").credit("V1") == ""  # no name unless the scholar agreed
    pending = approved_review(plan, "V1", "الشيخ فلان")
    pending.data["units"]["u-allah"]["status"] = "scholar_review"  # type: ignore[index]
    assert any("u-allah" in m for m in pending.problems("V1", units))
    partial = approved_review(plan, "V1")
    partial.data["volumes"]["V1"]["units"].remove("u-house")  # type: ignore[index]
    assert any("u-house" in m for m in partial.problems("V1", units))
    path = tmp_path / "export.json"
    path.write_text('{"version": 1, "volumes": {"V1": {"approved": false}}, "units": {}}', encoding="utf-8")
    monkeypatch.setenv(iv.REVIEW_ENV, str(path))
    assert iv.Review.load().path == path and "V1 is not approved by the scholar" in iv.Review.load().problems(
        "V1", units
    )


def test_a_print_build_refuses_unapproved_sources_missing_pages_and_writes_nothing(
    plan: islamic.Plan, resolver: Any, tmp_path: Path
) -> None:
    content = iv.check_volume(plan, "V1", resolver, print_build=True, review=approved_review(plan, "V1"))
    codes = {p.code for p in content.errors}
    assert "not-approved" in codes and "not-reviewed" not in codes  # the sources wait for the scholar
    out = tmp_path / "v1"
    with pytest.raises(iv.VolumeRefused, match="not scholar_approved"):
        asyncio.run(
            iv.render_volume(
                "v1",
                Child("ليان", "f"),
                out,
                print_build=True,
                resolver=resolver,
                review=approved_review(plan, "V1"),
            )
        )
    assert not (out / "interior.pdf").exists()
    unreviewed = iv.check_volume(plan, "V1", resolver, print_build=True, review=iv.Review({}, None))
    assert "not-reviewed" in {p.code for p in unreviewed.errors}


def test_the_scholars_name_prints_only_when_the_export_gives_it(resolver: Any) -> None:
    cert = parse_page({"id": "c", "type": "certificate", "title": "شَهَادَةٌ", "statement": "أَنَا", "fields": ["name"], "reviewed_by_line": True})  # fmt: skip
    with pytest.raises(PageProblems, match="scholar's name"):
        build_pages(book_of([cert], resolver), ASSETS)
    context = IslamicContext(resolver, Kit(), "print", DATE, credit="الشيخ فلان")
    title = parse_page({"id": "t", "type": "front-title", "title": "عُنْوَانٌ"})
    book = BookSpec(
        "islamic", "ق", Child("ليان", "f"), (page_spec(cert, 1, context), page_spec(title, 2, context)), DATE,
        geometry=product_geometry("family"),
    )  # fmt: skip
    built = build_pages(book, ASSETS)
    assert [p.built.data["credit"] for p in built] == ["راجعه علميًّا: الشيخ فلان"] * 2


# ---- a rendered slice of V1 --------------------------------------------------------------------------------


def test_a_slice_of_v1_renders_to_print_ready_pdfs(plan: islamic.Plan, resolver: Any, tmp_path: Path) -> None:
    files = asyncio.run(
        iv.render_volume(
            "v1",
            Child("يوسف", "m"),
            tmp_path,
            resolver=resolver,
            day=dt.date(2026, 10, 1),
            only={"front/", "u-blessings/", "end/"},
        )
    )
    assert files.interior.exists() and files.cover.exists()
    assert files.pages == 5 + 13 + 5  # the front pages, the unit «نِعَمُ رَبِّي» (13 pages), the final pages
    assert files.passed, {k: [c for c in r["checks"] if not c["ok"]] for k, r in files.preflight.items()}
    assert set(files.preflight) == {"interior.pdf", "cover.pdf"}


def test_a_prophets_units_picture_pages_show_no_people(plan: islamic.Plan, resolver: Any) -> None:
    assert {"u-adam", "u-yunus", "u-sira"} <= iv.prophets_units(plan, "V4")
    assert iv.prophets_units(plan, "V1") == {"u-prophet", "u-follow"}
    maze = {"key": "u-nuh/l1-2", "type": "maze", "goal": "tree", "runner": "reader"}
    content = iv.check_volume(plan, "V4", resolver, entries=[maze], build=False)
    assert "depiction" in {p.code for p in content.errors}
    ship = {**maze, "runner": "ship"}
    assert iv.check_volume(plan, "V4", resolver, entries=[ship], build=False).errors == []
