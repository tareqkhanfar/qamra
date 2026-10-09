"""Every QR code an activity book prints opens a page that works (owner, 2026-10-09: «بدي أفتح أي دوسية ولما
أسوي الكيو آر لازم يشتغل… ما عدا الدوسية الإسلامية ما عليها كيو آر»).

Each product is rendered as its print HTML (interiors, covers, the sticker and insert sheets), every printed
QR is decoded from its vector (`printed_qr.decode`, what a phone reads) and must be one of the site's routes
on https://qamra.app, resolved the way the API resolves it:
- «رحلتي الأولى للتعلّم»: every audio page prints exactly one QR, to `/a/{code}`, a code of the API's catalog
  (content/journey/audio.yaml); every catalog item is printed somewhere, so nothing in it is unreachable.
- «دوسية التأسيس», «مغامراتي مع عائلتي» and «قلبي يعرف الله» print no QR at all (no audio behind them: the
  foundation's audio-QR add-on is off, the Islamic recitations aren't recorded; `islamic_content.AUDIO_QR`).
- A page that asks for audio without a playable code prints no QR and no empty «امسح» card
  (`engine.audio_qr`).
The story books' «صوت أهلي» codes: packages/ai/tests/test_voice_qr.py; the e2e scan:
tests/e2e/test_qr_codes.py.
"""

import dataclasses
import re
from collections.abc import Iterator
from typing import Any

import pytest
from printed_qr import QR_SVG, WEB_APP, qr_by_page, qr_urls, route
from qamra_workbook import islamic
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.journey_book import PLAN as JOURNEY_PLAN
from qamra_workbook.journey_book import audio_items, built_stages, load_layer
from qamra_workbook.journey_book import load as load_journey
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render import islamic_volume as iv
from qamra_workbook.render.engine import book_html, build_pages
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import cover_specs as family_covers
from qamra_workbook.render.family import insert_sheets, plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.islamic_content import AUDIO_QR, IslamicContext
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import BookSpec, Child, Family, Member, PageSpec
from qamra_workbook.render.stickers import sheet_book
from qamra_workbook.render.workbook import LEVELS, VOLUMES, volume_specs
from test_islamic_pages import DATE, fake_resolver

from qamra_api import journey_audio

ASSETS = Assets(LibraryStore())
DOMAIN = "qamra.app"
GIRL = Child("ليان", "f")
FAMILY = Family("الخطيب", (Member("ماما", scarf=True), Member("بابا"), Member("أخي", "كرم")), "رام الله")
# anything that looks like a QR box in the print HTML (the journey's cards, the story's corner, the covers')
QR_BOXES = re.compile(r'class="(?:qr-card|en-qr|j-qr|voice-qr|su-qr card|dk-qr card)"')


def printed(book: BookSpec) -> tuple[list[Any], str]:
    pages = build_pages(book, ASSETS)
    return pages, book_html(book, pages, ASSETS)


def no_qr(html: str) -> None:
    assert QR_SVG.search(html) is None and QR_BOXES.search(html) is None


def test_the_web_routes_match() -> None:
    """The routes `printed_qr.route` accepts are the web app's own (a QR to anything else is a dead end)."""
    audio = (WEB_APP / "a/[code]/page.tsx").read_text(encoding="utf-8")
    listen = (WEB_APP / "v/[token]/[page]/page.tsx").read_text(encoding="utf-8")
    assert "/^[a-z2-7]{4,16}$/.test(code)" in audio
    assert "beat < 1 || beat > 99" in listen and (WEB_APP / "v/[token]/page.tsx").is_file()
    assert frozenset("abcdefghijklmnopqrstuvwxyz234567") == journey_audio.CODE_CHARS
    assert route("https://qamra.app/a/ogjmg6ob") == ("audio", {"code": "ogjmg6ob"})
    for dead in (
        "http://qamra.app/a/ogjmg6ob",  # never http
        "https://203.0.113.7/a/ogjmg6ob",  # never an address
        "https://qamra.app/a/v2-u-why-pray-l3-2",  # an Islamic page id is no player code
        "https://qamra.app/a/journey-s1-p28",
        "https://qamra.app/how-it-works",
    ):
        assert route(dead) is None, dead


# ---- «رحلتي الأولى للتعلّم» --------------------------------------------------------------------------------


def journey_books() -> Iterator[tuple[int, BookSpec, BookSpec]]:
    for stage in built_stages():
        interior, cover = stage_specs(GIRL, stage, domain=DOMAIN, name_en="Layan")
        yield stage, interior, cover


def test_every_journey_qr_opens_its_sound_and_every_sound_is_printed() -> None:
    printed_codes: set[str] = set()
    for stage, interior, cover in journey_books():
        pages, html = printed(interior)
        by_page = qr_by_page(html)
        for page in pages:
            urls = by_page.get(page.spec.id, [])
            if not page.spec.audio:
                assert urls == [], f"stage {stage} p{page.spec.number} prints a QR without audio"
                continue
            assert len(urls) == 1, f"stage {stage} p{page.spec.number} ({page.spec.type}): {urls}"
            found = route(urls[0], DOMAIN)
            assert found is not None and found[0] == "audio", urls[0]
            code = found[1]["code"]
            assert code == page.spec.params["audio_code"]
            assert journey_audio.item(code) is not None, f"{code} is not in content/journey/audio.yaml"
            printed_codes.add(code)
        assert len(qr_urls(html)) == sum(1 for p in pages if p.spec.audio)  # no stray QR anywhere
        assert len(QR_SVG.findall(html)) == len(
            re.findall(r'class="(?:qr-card|en-qr)"', html)
        )  # no empty box
        _, cover_html = printed(cover)
        no_qr(cover_html)  # the covers and the certificate pages carry none
        _, stickers = printed(sheet_book(interior))
        no_qr(stickers)
    catalog = {i.code for s in built_stages() for i in audio_items(load_journey(JOURNEY_PLAN), load_layer(s))}
    assert printed_codes == catalog == set(journey_audio.catalog())


def test_a_page_with_audio_but_no_playable_code_prints_no_qr() -> None:
    _, interior, _ = next(journey_books())
    page = next(p for p in interior.pages if p.audio)
    dead = [
        dataclasses.replace(page, params={k: v for k, v in page.params.items() if k != "audio_code"}),
        dataclasses.replace(page, params={**page.params, "audio_code": "v2-u-why-pray-l3-2"}),
    ]
    for spec in dead:
        _, html = printed(dataclasses.replace(interior, pages=(spec,)))
        no_qr(html)


# ---- the books with no audio: no QR at all ---------------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_the_foundation_volumes_print_no_qr(level: str) -> None:
    for number in VOLUMES:
        interior, cover, _, _ = volume_specs(GIRL, level, number, name_en="Layan", domain=DOMAIN)
        assert not any(p.audio for p in interior.pages)
        for book in (interior, cover):
            no_qr(printed(book)[1])


def test_the_family_book_prints_no_qr() -> None:
    plan = load_family(FAMILY_PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    books: list[tuple[PageSpec, ...]] = [tuple(specs), tuple(family_covers(plan))]
    books += [tuple(sheets) for _, sheets in insert_sheets(plan)]
    for pages in books:
        no_qr(printed(family_spec(pages, GIRL, FAMILY))[1])


def test_the_islamic_volumes_keep_their_qr_codes_hidden() -> None:
    assert AUDIO_QR is False  # no recitation is recorded yet: a QR there would lead nowhere
    plan, resolver = islamic.load(), fake_resolver()
    for vid in plan.volumes:
        context = IslamicContext(resolver, Kit(), "preview", DATE)
        book = iv.volume_book(plan, iv.check_volume(plan, vid, resolver), context, GIRL)
        assert not any(p.audio for p in book.pages)
        for each in (book, iv.cover_book(plan, vid, context, book), sheet_book(book)):
            no_qr(printed(each)[1])
