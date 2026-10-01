"""The source system of «قلبي يعرف الله» (Addendum 10 §3): the resolver on a FAKE corpus (nothing here is
Quran or hadith),
marker extraction, status gating, the register merge and every check failing on a deliberately bad page."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from qamra_workbook import islamic_checks as checks
from qamra_workbook.islamic_sources import (
    Candidate,
    Register,
    Resolver,
    SourceError,
    Span,
    cut,
    letters,
    load,
    parse_quran,
    sha256,
)

# fake Arabic words with harakat: obviously not religious wording
FAKE_HADITH = "حَدَّثَنَا فُلَانٌ، قَالَ: كَلِمَةٌ تَجْرِيبِيَّةٌ أُولَى، ثُمَّ جُمْلَةٌ اخْتِبَارِيَّةٌ ثَانِيَةٌ، وَخَاتِمَةٌ وَهْمِيَّةٌ."
FAKE_QURAN = "# FAKE FILE: layout and tests only\n1|1|FAKE-VERSE-1\n1|2|FAKE-VERSE-2\n"

MAIN: dict[str, Any] = {
    "corpus": {
        "quran": {"file": "content/islamic/quran/fake.txt"},
        "hadith": {"dataset": "fake/dataset", "editions": {"bukhari": "ara-fake"}},
    },
    "sources": [
        {
            "id": "q-fake",
            "kind": "quran",
            "title_ar": "آية اختبار",
            "quran": {"surah": 1, "from": 1, "to": 2},
        },
        {
            "id": "h-fake",
            "kind": "hadith",
            "title_ar": "حديث اختبار",
            "hadith": {"collection": "bukhari", "number": 1},
            "expect": ["تجريبية"],
            "scholar_decision": "سؤال اختبار للمشرف",
        },
        {
            "id": "d-fake",
            "kind": "dua",
            "title_ar": "ذكر اختبار",
            "dua": {"from": "h-fake", "start": "كلمة", "end": "أولى"},
        },
        {"id": "s-fake", "kind": "sira", "title_ar": "واقعة اختبار"},
        {"id": "r-fake", "kind": "ruling", "title_ar": "حكم اختبار", "basis": ["h-fake"]},
    ],
}


def candidate(text: str = FAKE_HADITH, check: str = "matched") -> dict[str, Candidate]:
    # type: ignore[arg-type]
    entry = Candidate("h-fake", "hadith", text, sha256(text), check, "fake/dataset", "ara-fake", 1)
    return {"h-fake": entry}


def resolver(
    *, quran: bool = True, cands: dict[str, Candidate] | None = None, main: dict[str, Any] | None = None
) -> Resolver:
    reg = Register.from_dicts(main or MAIN)
    return Resolver(reg, parse_quran(FAKE_QURAN) if quran else None, candidate() if cands is None else cands)


# ---- matching on the letters only
# ----------------------------------------------------------------------------


def test_letters_ignore_harakat_tatweel_punctuation_and_fold_alef_forms() -> None:
    assert letters("بِسْمِ  اللَّهِ") == letters("بسم الله") == "بسمالله"
    assert letters("الْإِخْلَاصِ") == letters("الاخلاص")
    assert letters("كـــلمة،") == "كلمه"
    assert letters("ﷲ") == letters("الله")  # presentation forms expand to their letters


def test_cut_returns_the_original_slice_with_its_harakat() -> None:
    words, starts = cut(FAKE_HADITH, Span("كلمة", "أولى"))  # markers typed without harakat
    assert words == "كَلِمَةٌ تَجْرِيبِيَّةٌ أُولَى"
    assert starts == 1
    again, _ = cut(FAKE_HADITH, Span("كَلِمَةٌ", "أُولَى"))  # markers typed with harakat
    assert again == words


def test_cut_may_use_the_same_words_as_both_markers() -> None:
    assert cut(FAKE_HADITH, Span("جملة", "جملة"))[0] == "جُمْلَةٌ"


def test_cut_fails_loudly_on_a_marker_that_is_not_there() -> None:
    with pytest.raises(SourceError, match="not found"):
        cut(FAKE_HADITH, Span("غير موجودة", "أولى"))
    with pytest.raises(SourceError, match="end marker"):
        cut(FAKE_HADITH, Span("كلمة", "لا توجد"))
    with pytest.raises(SourceError, match="no letters"):
        cut(FAKE_HADITH, Span("", "أولى"))


# ---- the resolver and the status ladder
# ---------------------------------------------------------------------


def test_quran_is_copied_from_the_file_and_the_placeholder_shows_without_it() -> None:
    got = resolver().resolve("q-fake")
    assert got.text == "FAKE-VERSE-1 FAKE-VERSE-2"
    assert [n for n, _ in got.lines] == [1, 2]
    assert got.status == "text_verified"
    missing = resolver(quran=False).resolve("q-fake")
    assert missing.text is None and missing.placeholder
    assert "طنزيل" in missing.notice  # the marked placeholder block's text
    assert missing.status == "proposed"


def test_hadith_candidate_status_and_a_mismatch_is_not_printed() -> None:
    assert resolver().resolve("h-fake").status == "text_candidate"
    bad = resolver(cands=candidate(check="mismatch")).resolve("h-fake")
    assert bad.text is None and "mismatch" in bad.placeholder
    assert resolver(cands={}).resolve("h-fake").text is None  # never fetched


def test_dua_is_a_span_of_its_hadith_and_follows_it() -> None:
    got = resolver().resolve("d-fake")
    assert got.text == "كَلِمَةٌ تَجْرِيبِيَّةٌ أُولَى" and got.status == "text_candidate"
    assert resolver(cands={}).resolve("d-fake").text is None
    broken = {
        **MAIN,
        "sources": [
            *MAIN["sources"][:2],
            {**MAIN["sources"][2], "dua": {"from": "h-fake", "start": "كلمة", "end": "ثالثة"}},
        ],
    }
    with pytest.raises(SourceError, match="d-fake"):
        resolver(main=broken).resolve("d-fake")


def test_a_page_level_span_cuts_a_source() -> None:
    got = resolver().resolve("h-fake", {"start": "جملة", "end": "ثانية"})
    assert got.text == "جُمْلَةٌ اخْتِبَارِيَّةٌ ثَانِيَةٌ"


def test_sira_and_ruling_have_no_text_to_print() -> None:
    for source_id in ("s-fake", "r-fake"):
        got = resolver().resolve(source_id)
        assert got.text is None and not got.text_expected


def test_a_text_that_changed_after_it_was_verified_fails_loudly() -> None:
    sources = [dict(s) for s in MAIN["sources"]]
    sources[1] |= {"status": "text_verified", "approved_sha256": "0" * 64}
    with pytest.raises(SourceError, match="changed"):
        resolver(main={**MAIN, "sources": sources}).resolve("h-fake")


# ---- loading and merging the register
# -----------------------------------------------------------------------


def test_load_merges_sources_d_and_refuses_duplicate_ids(tmp_path: Path) -> None:
    (tmp_path / "sources.d").mkdir()
    main = {"version": 1, "corpus": MAIN["corpus"], "sources": MAIN["sources"][:2]}
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump(main, allow_unicode=True), "utf-8")
    (tmp_path / "sources.d" / "b.yaml").write_text(
        yaml.safe_dump({"sources": MAIN["sources"][2:3]}, allow_unicode=True), "utf-8"
    )
    (tmp_path / "sources.d" / "a.yaml").write_text(
        yaml.safe_dump({"sources": MAIN["sources"][3:]}, allow_unicode=True), "utf-8"
    )
    reg = load(tmp_path / "sources.yaml")
    assert [s.id for s in reg.sources] == [
        "q-fake",
        "h-fake",
        "s-fake",
        "r-fake",
        "d-fake",
    ]  # a.yaml before b.yaml
    assert reg.origin["d-fake"] == "b.yaml"
    (tmp_path / "sources.d" / "c.yaml").write_text(
        yaml.safe_dump({"sources": [MAIN["sources"][0]]}, allow_unicode=True), "utf-8"
    )
    with pytest.raises(SourceError, match="duplicate source id 'q-fake'"):
        load(tmp_path / "sources.yaml")


def test_a_malformed_row_names_its_file_and_id(tmp_path: Path) -> None:
    (tmp_path / "sources.yaml").write_text(
        yaml.safe_dump(
            {"corpus": MAIN["corpus"], "sources": [{"id": "x", "kind": "hadith", "title_ar": "ت"}]},
            allow_unicode=True,
        ),
        "utf-8",
    )
    with pytest.raises(SourceError, match=r"sources\.yaml: source 'x'"):
        load(tmp_path / "sources.yaml")


def test_the_real_register_loads_with_unique_ids() -> None:
    reg = load()
    assert len(reg.sources) == len({s.id for s in reg.sources}) > 100
    assert {s.kind for s in reg.sources} <= {"quran", "hadith", "dua", "sira", "ruling"}


# ---- the checks: each fails on a deliberately bad page
# --------------------------------------------------------

RULES = checks.PageRules(
    {"prophet-story": True, "dhikr": True, "coloring": False, "wwyd": True, "unit-review": True}
)


def codes(page: dict[str, Any], res: Resolver | None = None) -> list[str]:
    return [p.code for p in checks.check_page(page, res or resolver(), RULES)]


def test_a_good_page_passes() -> None:
    page = {
        "id": "p",
        "type": "dhikr",
        "dhikr": {"source": "d-fake"},
        "why": {"text": "ت", "sources": ["q-fake"]},
        "manner": {"text": "ت", "sources": ["h-fake"]},
    }
    assert codes(page) == []


def test_an_unsourced_block_fails() -> None:
    assert "no-source" in codes(
        {"id": "p", "type": "dhikr", "dhikr": {}, "why": {"text": "ت", "sources": ["q-fake"]}}
    )
    assert "no-source" in codes(
        {"id": "p", "type": "dhikr", "dhikr": {"source": "d-fake"}, "why": {"text": "ت"}}
    )  # a religious statement
    assert "no-source" in codes({"id": "p", "type": "wwyd", "quote": {"source": "h-fake"}, "sources": []})


def test_an_unknown_id_and_a_wrong_kind_fail() -> None:
    assert "unknown-source" in codes({"id": "p", "type": "dhikr", "dhikr": {"source": "d-nope"}})
    assert "wrong-kind" in codes({"id": "p", "type": "surah", "verse": {"source": "h-fake"}})


def test_dua_from_must_be_a_hadith() -> None:
    bad = {
        **MAIN,
        "sources": [
            *MAIN["sources"][:3],
            {**MAIN["sources"][2], "id": "d-bad", "dua": {"from": "q-fake", "start": "a", "end": "b"}},
        ],
    }
    found = checks.check_register(resolver(main=bad))
    assert any(p.code == "bad-dua" and p.where == "d-bad" for p in found)
    missing = {
        **MAIN,
        "sources": [{**MAIN["sources"][2], "dua": {"from": "h-gone", "start": "a", "end": "b"}}],
    }
    assert any(p.code == "bad-dua" for p in checks.check_register(resolver(main=missing)))


def test_a_marker_that_does_not_match_fails_the_register() -> None:
    bad = {
        **MAIN,
        "sources": [
            *MAIN["sources"][:2],
            {**MAIN["sources"][2], "dua": {"from": "h-fake", "start": "كلمة", "end": "ثالثة"}},
        ],
    }
    assert any(p.code == "marker" for p in checks.check_register(resolver(main=bad)))


def test_a_verse_on_a_coloring_page_fails() -> None:
    page = {
        "id": "c",
        "type": "coloring",
        "sacred_text": "none",
        "art": "blessings-garden",
        "verse": {"source": "q-fake"},
    }
    assert "sacred-page" in codes(page)
    assert "sacred-page" in codes(
        {"id": "c", "type": "coloring", "art": "x", "title": "ت", "sources": ["q-fake"]}
    )
    assert codes({"id": "c", "type": "coloring", "sacred_text": "none", "art": "blessings-garden"}) == []


def test_a_figure_in_a_prophet_scene_fails_but_the_narrator_may_show_the_cast() -> None:
    base = {
        "id": "p",
        "type": "prophet-story",
        "tags": ["prophet_story"],
        "narrator": {"figures": ["huda", "reem", "salem"]},
    }
    ok = {**base, "scenes": [{"art": "ship-at-sea", "text": "ت", "sources": ["q-fake"]}]}
    assert "depiction" not in codes(ok)
    declared = {
        **base,
        "scenes": [{"art": "ship-at-sea", "text": "ت", "sources": ["q-fake"], "figures": ["huda"]}],
    }
    assert "depiction" in codes(declared)
    drawn = {**base, "scenes": [{"art": "family-meal", "text": "ت", "sources": ["q-fake"]}]}
    assert "depiction" in codes(drawn)  # the art itself draws people
    prophet = {
        **base,
        "narrator": {"figures": ["yunus"]},
        "scenes": [{"art": "ship-at-sea", "text": "ت", "sources": ["q-fake"]}],
    }
    assert "depiction" in codes(prophet)


def test_a_print_build_fails_on_a_placeholder_and_on_unapproved_sources() -> None:
    page = {
        "id": "p",
        "type": "surah",
        "verse": {"source": "q-fake"},
        "meaning": {"text": "ت", "sources": ["q-fake"]},
    }
    found = {p.code for p in checks.check_print([page], resolver(quran=False))}
    assert found == {"placeholder", "not-approved"}  # q-fake has no text and nothing is approved
    assert {p.code for p in checks.check_print([page], resolver())} == {"not-approved"}


def test_a_print_build_passes_when_everything_is_approved() -> None:
    sources = [dict(s) for s in MAIN["sources"]]
    for s in sources:
        s |= {"status": "scholar_approved", "reviewed_by": "اختبار", "reviewed_on": "2026-10-01"}
    for s in sources[1:3]:
        s["approved_sha256"] = candidate()["h-fake"].sha if s["kind"] == "hadith" else sha256("x")
    res = resolver(main={**MAIN, "sources": sources})
    page = {
        "id": "p",
        "type": "dhikr",
        "dhikr": {"source": "d-fake"},
        "why": {"text": "ت", "sources": ["q-fake"]},
    }
    assert checks.check_print([page], res) == []


def test_typed_wording_fails_on_a_sacred_page_and_a_token_does_not() -> None:
    res = resolver()
    typed = {
        "id": "p",
        "type": "unit-review",
        "choose": {
            "text": "ت",
            "sources": ["q-fake"],
            "choices": [{"t": "كَلِمَةٌ تَجْرِيبِيَّةٌ أُولَى", "ok": True}, {"t": "جواب عادي"}],
        },
    }
    assert codes(typed, res) == ["typed-wording"]  # the plain option stays typed
    sourced = {
        "id": "p",
        "type": "unit-review",
        "choose": {
            "text": "ت",
            "sources": ["q-fake"],
            "choices": [{"source": "d-fake", "ok": True}, {"t": "جواب عادي"}],
        },
    }
    assert codes(sourced, res) == []
    token = {
        "id": "p",
        "type": "unit-review",
        "habit": {"text": "قولوا {src:d-fake} دائمًا", "sources": ["q-fake"]},
    }
    assert codes(token, res) == []
    assert "unknown-source" in codes(
        {"id": "p", "type": "unit-review", "habit": {"text": "{src:d-nope}", "sources": ["q-fake"]}}, res
    )
    assert "sacred-page" in codes(
        {"id": "c", "type": "coloring", "sacred_text": "none", "art": "x", "title": ("كَلِمَةٌ تَجْرِيبِيَّةٌ أُولَى")},
        res,
    )


def test_a_choice_is_typed_or_sourced_not_both_or_neither() -> None:
    both = {
        "id": "p",
        "type": "unit-review",
        "choose": {
            "text": "ت",
            "sources": ["q-fake"],
            "choices": [{"t": "جواب", "source": "d-fake"}, {"ok": True}],
        },
    }
    assert codes(both).count("bad-choice") == 2


def test_the_scholar_queue_lists_open_decisions_with_the_pages_that_use_them() -> None:
    page = {"id": "p1", "type": "dhikr", "dhikr": {"source": "d-fake"}}
    queue = checks.scholar_queue(resolver(), [page])
    assert [(d.source, d.pages) for d in queue] == [
        ("h-fake", ("p1",))
    ]  # a dua's question reaches the pages that print it
    assert queue[0].question == "سؤال اختبار للمشرف"


def test_the_sample_pages_use_a_register_with_no_error() -> None:
    from qamra_workbook.islamic_sources import SAMPLES

    res = Resolver.load()
    found = checks.errors(checks.check_pages(checks.load_pages(SAMPLES), res, checks.PageRules.load()))
    assert found == []
