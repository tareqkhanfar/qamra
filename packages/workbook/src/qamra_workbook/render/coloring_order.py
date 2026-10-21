"""One personalized copy of a «دفاتر التلوين والرسم» book for an order (no AI cost): the interior (fixed line
art, the child's title page and «عن قمرة» with the book code) and the cover (front and back on card, the
child's name, and their character when the family has one), each with its preflight report.

The worker's order job (`qamra_worker.jobs.coloring_book`) calls `render_order`; the CLI
(`python -m qamra_workbook.render.coloring --title letters`) renders samples the same way.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from qamra_pdf.imprint import Imprint
from qamra_workbook.render.journey_order import OrderFiles
from qamra_workbook.render.spec import Child, Numerals


async def render_order(
    child: Child,
    title: str,
    out: Path,
    *,
    numerals: Numerals = "hindi",
    day: dt.date | None = None,
    domain: str = "qamra.app",
    imprint: Imprint | None = None,
) -> OrderFiles:
    """Every file of one copy into `out`: interior.pdf and cover.pdf (`OrderFiles`, preflight per file).

    `title`: a key or a store slug of `qamra_workbook.coloring.titles.TITLES`. `child.character_sheet` may be
    None: the cover is then drawn without the character."""
    from qamra_workbook.render.coloring import render_copy

    return await render_copy(child, title, out, numerals=numerals, day=day, domain=domain, imprint=imprint)
