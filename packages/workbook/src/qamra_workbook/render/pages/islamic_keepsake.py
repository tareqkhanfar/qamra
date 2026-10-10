"""«قلبي يعرف الله»: the keepsake pages: the little Muslim's passport (a stamp for each unit and a star for
each challenge),
the certificate, and a surah page (the verses in a dignified frame, the recitation's QR, a memorisation
tracker).

The passport and the certificate are pages the child keeps and may colour or stick on: they carry no verse,
hadith or dhikr
(Addendum 10 §3.6). Their statement is the child's own: «أنا مسلم صغير أحب الله وأقتدي بنبيي محمد ﷺ». The
surah page is the
opposite: it carries a whole surah, never goes on a coloured or cut page, and asks the family to keep it
clean.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from qamra_pdf.arabic_names import genitive
from qamra_workbook.pictures.islamic import glyph_svg, star8_svg, unit_glyph
from qamra_workbook.render.islamic_content import Certificate, Passport, Surah
from qamra_workbook.render.islamic_units import volume_units
from qamra_workbook.render.pages.family import uri
from qamra_workbook.render.pages.islamic_common import (
    chrome,
    claim,
    context_of,
    islamic_page,
    page_of,
    references,
    rich,
    sacred,
    source_ids,
)
from qamra_workbook.render.registry import Built, PageContext

GOLD = "#C9962B"


def stamp_art(glyph: str, color: str) -> Markup:
    """The ghost of a unit's sticker: a ring, the unit's icon in its colour, to stick the real one over."""
    return Markup(  # nosec B704 (static art)
        '<svg class="stamp-art" viewBox="0 0 40 40" aria-hidden="true">'
        f'<circle cx="20" cy="20" r="18.2" fill="{color}" opacity="0.14"/>'
        f'<circle cx="20" cy="20" r="18.2" fill="none" stroke="{color}" '
        f'stroke-width="0.9" stroke-dasharray="2.2 2"/>'
        f'<g transform="translate(9.2 9.2) scale(0.9)" opacity="0.7">{glyph_svg(glyph, color, 1.7)}</g></svg>'
    )


@islamic_page("muslim-passport")
def muslim_passport(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Passport)
    problems: list[str] = []
    units = volume_units(page.volume)
    if not units:
        problems.append(f"no units in volume {page.volume!r} (units.yaml)")
    stamps = [
        {
            "title": ctx.text(u.title_ar),
            "n": ctx.num(i),
            "art": stamp_art(unit_glyph(u.icon), u.color),
            "color": u.color,
            "ink": u.on_color,
        }
        for i, u in enumerate(units, start=1)
    ]
    child = ctx.book.child
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "card": page.layout == "journey-card",
        "photo": uri(ctx.assets.character),
        "name": child.name,
        "date": "",  # a line the family fills in: the print date is not the day the journey starts
        "stamps": stamps,
        "stars": [ctx.num(i) for i in range(1, page.challenge_stars + 1)],
        "star": star8_svg(GOLD, 9.0, "#1F5A46"),
        "labels": {
            "series": "قلبي يعرف الله",
            "name": "اسْمِي",
            "date": "بَدَأْتُ رِحْلَتِي فِي",
            "sign": "تَوْقِيعِي",
            "stamps": "أَخْتَامُ وَحَدَاتِي",
            "stars": "نُجُومُ تَحَدِّيَاتِي",
            "stick": ctx.text("{أَلْصِقِ/أَلْصِقِي} الْمُلْصَقَ بَعْدَ كُلِّ وَحْدَةٍ"),
            "steps": "رِحْلَتِي خُطْوَةً خُطْوَةً",
            "colour": ctx.text("{لَوِّنْ/لَوِّنِي} نَجْمَةً بَعْدَ كُلِّ تَحَدٍّ"),
        },
    }
    return Built(data, None, problems)


@islamic_page("muslim-certificate")
def muslim_certificate(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Certificate)
    problems: list[str] = []
    credit = context_of(ctx).credit
    if page.reviewed_by_line and not credit:
        problems.append(
            "the «راجعه علميًا» line needs the scholar's name from the review workflow (Addendum 10 §3.3)"
        )
    child = ctx.book.child
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "statement": ctx.text(page.statement),
        "character": uri(ctx.assets.character),
        "name": genitive(child.name),  # after «تُمْنَحُ هَذِهِ الشَّهَادَةُ إِلَى»: «أبي بكر»
        "date": "",  # written on the day the child finishes the book, not the day it was printed
        "star": star8_svg(GOLD, 11.0, "#FFFBEE"),
        "fields": page.fields,
        "credit": f"راجعه علميًّا: {credit}" if page.reviewed_by_line and credit else "",
        "labels": {
            "series": "قلبي يعرف الله",
            "date": "التَّارِيخُ",
            "sign": "تَوْقِيعُ الْأَهْلِ",
            "give": "تُمْنَحُ هَذِهِ الشَّهَادَةُ إِلَى",
        },
    }
    return Built(data, None, problems)


@islamic_page("surah-page")
def surah_page(ctx: PageContext) -> Built:
    page = page_of(ctx)
    assert isinstance(page, Surah)
    problems: list[str] = []
    for flag in ("never_cut", "never_colored"):
        if flag not in page.flags:
            problems.append(f"a surah page must carry the flag {flag!r} (it is never cut or coloured)")
    block = sacred(ctx, page.verse, "verse", problems)
    ayahs = max(page.tracker.ayahs, 1)
    data: dict[str, Any] = {
        "chrome": chrome(ctx, problems),
        "verse": block,
        "meaning": claim(ctx, page.meaning, problems),
        "rows": [ctx.num(i) for i in range(1, ayahs + 1)],
        "days": [ctx.num(i) for i in range(1, page.tracker.days + 1)],
        "care": rich(ctx, page.care_note, problems),
        "labels": {
            "meaning": "مَعْنَى السُّورَةِ",
            "listen": ctx.text("{اسْمَعِ/اسْمَعِي} التِّلَاوَةَ"),
            "tracker": "جَدْوَلُ حِفْظِي",
            "ayah": "الْآيَةُ",
            "day": "الْيَوْمُ",
        },
        "refs": references(ctx, [page.verse.source, *source_ids(page.meaning)]),
    }
    return Built(data, None, problems)
