"""Look at drawings while drawing them: SVG in mm → PNG through Chromium (the same engine that prints).

    from qamra_workbook.coloring.snap import snap
    snap({"sheep": svg_markup, "tree": other}, out_dir, dpi=110)      # one PNG per drawing

`uv run python -m qamra_workbook.coloring.preview …` renders whole pages; this module is the quick loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path

from playwright.async_api import async_playwright

_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html, body {{ margin: 0; background: #fff; }}
.cell {{ display: inline-block; padding: 4mm; vertical-align: top; }}
svg {{ display: block; }}
</style></head><body><div class="cell" id="cell">{body}</div></body></html>"""


async def _snap(drawings: Mapping[str, str], out: Path, dpi: int) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(device_scale_factor=dpi / 96)
            for name, markup in drawings.items():
                await page.set_content(_PAGE.format(body=markup), wait_until="load")
                path = out / f"{name}.png"
                await page.locator("#cell").screenshot(path=str(path))
                paths.append(path)
        finally:
            await browser.close()
    return paths


def snap(drawings: Mapping[str, str], out: Path, dpi: int = 100) -> list[Path]:
    """Each drawing (an `<svg>` sized in mm) as `out/<name>.png` at `dpi`."""
    return asyncio.run(_snap(drawings, out, dpi))
