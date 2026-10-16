"""«رحلتي الأولى للتعلّم», QA of 2026-10-10: the certificate's date is left for the grown-up, a page of sounds
asks the parent to imitate them (there are no words to read), the «first letter of my name» review shows the
child's own letter, and memory and riddle answers are not always in the first place."""

from qamra_workbook.journey import load
from qamra_workbook.journey_book import PLAN, load_layer, page_specs, stage_book
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import build_pages
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import Child

ASSETS = Assets(LibraryStore())
GIRL = Child("ليان", "f")


def _pages(stage: int, numbers: set[int], child: Child = GIRL) -> dict[int, object]:
    specs = [p for p in page_specs(load(PLAN), load_layer(stage)) if p.number in numbers]
    return {p.spec.number: p for p in build_pages(stage_book(specs, child, name_en="Layan"), ASSETS)}


def test_the_certificates_leave_the_date_blank() -> None:
    for stage, n in ((1, 118), (2, 120)):
        cert = _pages(stage, {n})[n]
        assert cert.built.data["date"] == ""  # type: ignore[attr-defined]


def test_a_page_of_sounds_asks_the_parent_to_imitate_them() -> None:
    pages = _pages(1, {28, 32})
    assert "قلّدوها" in pages[28].built.data["qr_note"]  # type: ignore[attr-defined]  # animal sounds
    assert "اقرؤوا الكلمات" in pages[32].built.data["qr_note"]  # type: ignore[attr-defined]  # words


def test_the_name_letter_review_uses_the_childs_first_letter() -> None:
    page = _pages(2, {78})[78]
    assert any("«ل»" in line for line in page.built.answer)  # type: ignore[attr-defined]
    page = _pages(2, {78}, Child("سامي", "m"))[78]
    assert any("«س»" in line for line in page.built.answer)  # type: ignore[attr-defined]


def test_memory_and_riddle_answers_are_not_always_first() -> None:
    for stage, n in ((1, 8), (1, 14), (2, 6), (3, 6), (2, 117), (3, 114)):
        params = load_layer(stage).pages[n].params
        answer = params["answer"]
        first = params["choices"][0]
        assert first not in (answer if isinstance(answer, list) else [answer]), (stage, n)


def test_the_lemon_page_prints_the_word_its_title_and_clip_say() -> None:
    """Stage 3 p48: the title and the clip say «لَيْمون», the picture's label said «لَيْمونَة»."""
    page = _pages(3, {48})[48]
    assert "لَيْمونَة" not in str(page.built.data["word"])  # type: ignore[attr-defined]
    assert page.built.problems == []  # type: ignore[attr-defined]


def test_stage_one_arabic_stop_is_not_called_the_arabic_letters() -> None:
    """Stage 1 has no letter yet: its Arabic stop prepares reading; stages 2–3 keep «الحروف العربية»."""
    assert _pages(1, {85})[85].section_name == "الاستعداد للقراءة"  # type: ignore[attr-defined]
    assert _pages(3, {48})[48].section_name == "الحروف العربية"  # type: ignore[attr-defined]
