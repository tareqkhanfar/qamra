# ruff: noqa: E501  (Arabic fixtures are one line each)
"""«قلبي يعرف الله», the final round: the printer's multiple of four, the words said in the tashahhud, a verse's
citation that names exactly the ayat printed and reads in full, the vowelled salawat formula inside a hadith,
the «ماذا كنت ستفعل؟» feedback kept for the answer key, the unit's sources on its parents' page, the cast
barefoot where they pray, and no false statement about a prophet printed as a quiz option."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from qamra_workbook import islamic
from qamra_workbook.islamic_sources import (
    SALAWAT,
    Resolved,
    SourceError,
    Span,
    _ayat_of,
    cite,
    cut_out,
    load,
    vowel_salawat,
)
from qamra_workbook.pictures.islamic_backdrops import compose
from qamra_workbook.pictures.islamic_scenes import SCENES
from qamra_workbook.render import islamic_volume as iv
from qamra_workbook.render import people
from qamra_workbook.render.islamic_figures import Kit
from test_islamic_pages import fake_resolver

REPO = Path(__file__).resolve().parents[3]
PAGES = REPO / "content/islamic/pages"


@pytest.fixture(scope="module")
def plan() -> islamic.Plan:
    return islamic.load()


def test_every_volume_is_a_multiple_of_four_pages(plan: islamic.Plan) -> None:
    for vid in plan.volumes:
        assert len(plan.pages[vid]) % iv.PAGE_MULTIPLE == 0, vid
    assert not [p for p in islamic.problems(plan) if "multiple of" in p]


def test_the_build_refuses_a_page_count_that_is_not_a_multiple_of_four(plan: islamic.Plan) -> None:
    content, _ = iv.match_content(plan, "V2", [])
    content.slots = content.slots[:-1]  # one page short, as V2 was (119)
    problems = iv.page_count_problems(content)
    assert problems and problems[0].code == "page-count" and problems[0].level == "error"
    assert "119 pages" in problems[0].message
    content.slots = content.slots[:-3]
    assert iv.page_count_problems(content) == []


def test_a_dua_can_leave_out_a_stretch_of_its_hadith() -> None:
    text = "التَّحِيَّاتُ لِلَّهِ، الصَّالِحِينَ‏.‏ فَإِنَّكُمْ إِذَا قُلْتُمُوهَا أَصَابَتْ كُلَّ عَبْدٍ، أَشْهَدُ أَنْ لاَ إِلَهَ"
    out = cut_out(text, Span("فإنكم إذا قلتموها", "كل عبد"))
    assert "فَإِنَّكُمْ" not in out and "أَصَابَتْ" not in out
    assert out.startswith("التَّحِيَّاتُ لِلَّهِ، الصَّالِحِينَ") and out.endswith("أَشْهَدُ أَنْ لاَ إِلَهَ")
    with pytest.raises(SourceError):
        cut_out(text, Span("لا يوجد", "أبدا"))


def test_the_tashahhud_stops_with_the_words_said() -> None:
    src = load().by_id["d-tashahhud"]
    assert src.dua is not None and [g.start for g in src.dua.omit] == ["فإنكم إذا قلتموها"]
    words = fake_resolver().resolve("d-tashahhud").text or ""
    assert "فإنكم" not in words and "التحيات" in words and "ورسوله" in words


def test_a_spanned_verse_cites_exactly_the_ayat_printed() -> None:
    base = Resolved(
        id="q-x",
        kind="quran",
        title_ar="",
        status="text_verified",
        text="أ ب ت ث ج",
        lines=((1, "أ ب"), (2, "ت"), (3, "ث ج")),
        reference="97:1-3",
    )
    lines, ref = _ayat_of(base, 4, 5)  # «ت»: the whole of ayah 2
    assert ref == "97:2" and lines == ((2, "ت"),)
    lines, ref = _ayat_of(base, 6, 7)  # «ث»: a part of ayah 3 that stops before its end
    assert ref == "97:3" and lines == ((0, "ث"),)
    lines, ref = _ayat_of(base, 0, 5)
    assert ref == "97:1-2" and [n for n, _ in lines] == [1, 2]


def test_a_reference_reads_in_full() -> None:
    assert cite("7:31") == "سورة الأعراف: 31"
    assert cite("2:183-185") == "سورة البقرة: 183–185"
    assert (
        cite("صحيح البخاري 5376", lambda d: d.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")))
        == "صحيح البخاري: ٥٣٧٦"
    )
    assert cite("112:1-4").startswith("سورة الإخلاص")


def test_the_salawat_formula_is_vowelled_inside_a_hadith() -> None:
    assert vowel_salawat("قَالَ النَّبِيُّ صلى الله عليه وسلم ‏") == f"قَالَ النَّبِيُّ {SALAWAT} ‏"


def _pages() -> list[tuple[str, dict[str, Any]]]:
    out = []
    for f in sorted(PAGES.glob("*.yaml")):
        out += [(f.stem, p) for p in yaml.safe_load(f.read_text(encoding="utf-8"))["pages"]]
    return out


PROPHET = re.compile(r"ﷺ|نَبِيِّ|نَبِيُّ|نَبِيَّ|عَلَيْهِ السَّلَامُ|عَلَيْهِمَا السَّلَامُ")


def _false_statements(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        stem = node.get("text") or node.get("question") or ""
        for c in node.get("choices") or []:
            # a «who/what did he do?» question whose wrong option is a deed of his: «… ﷺ؟» + «تَرَكَهُ وَمَشَى»
            if isinstance(c, dict) and not c.get("ok") and isinstance(stem, str) and stem.endswith("؟"):
                deed = re.search(r"^(مَاذَا|بِمَاذَا|مَتَى|لِمَاذَا) (كَانَ )?(فَعَلَ|يَفْعَلُ|كَانَ|عَرَفَ|شَبَّهَ|طَمْأَنَ|خَفَّفَ)", stem)
                # a bare question about our Prophet ﷺ (no fact stated before it): its wrong option is about him
                about_him = (
                    "ﷺ" in stem and "." not in stem and not stem.startswith(("مَا اسْمُ", "مَنْ رَسُولُ", "كَيْفَ"))
                )
                if PROPHET.search(stem) and (deed or about_him):
                    found.append(f"{stem} ✗ {c.get('t')}")
        for st in node.get("statements") or node.get("true_false") or []:
            if isinstance(st, dict) and st.get("ok") is False and PROPHET.search(str(st.get("t", ""))):
                found.append(f"«خطأ»: {st.get('t')}")
        for v in node.values():
            found += _false_statements(v)
    elif isinstance(node, list):
        for v in node:
            found += _false_statements(v)
    return found


def test_no_false_statement_about_a_prophet_is_printed() -> None:
    found = [f"{v} {p['key']}: {s}" for v, p in _pages() for s in _false_statements(p)]
    assert not found, "\n".join(found)


def test_the_cast_pray_barefoot_and_keep_their_shoes_elsewhere() -> None:
    kit = Kit()
    hall = compose("mosque-inside", ["isl:prayer-mat"], ["huda", "salem"], "t", kit)
    street = compose("street", [], ["huda", "salem"], "t", kit)
    home_mat = compose("home", ["isl:prayer-mat"], ["reem"], "t", kit)
    assert people.SHOE not in hall and people.SHOE not in home_mat
    assert people.SHOE in street


def test_props_stand_in_the_scene_instead_of_floating_on_discs() -> None:
    svg = compose("home", ["isl:prayer-mat", "isl:wheat", "isl:lantern", "isl:cube"], [], "t", None)
    assert 'fill="#FFFFFF" opacity="0.92"' not in svg  # no white badge disc behind a series thing


def test_the_story_scenes_draw_no_people() -> None:
    from qamra_workbook.pictures.islamic_story_scenes import SCENES_EXTRA

    for name, scene in SCENES_EXTRA.items():
        assert not scene.figures and name in SCENES
        assert "<image" not in scene.draw("t", None)


def test_the_parents_page_lists_the_units_sources_with_what_they_support(plan: islamic.Plan) -> None:
    content = iv.check_volume(plan, "V5", fake_resolver(), build=False)
    ids = iv.unit_source_ids(content, "u-adab")
    assert "h-bukhari-5376" in ids
    register = load().by_id
    assert register["h-bukhari-5376"].label_ar == "التسمية والأكل باليمين"
    listed = [i for i in ids if register[i].kind in ("quran", "hadith")]
    assert all(register[i].label_ar for i in listed), [i for i in listed if not register[i].label_ar]
