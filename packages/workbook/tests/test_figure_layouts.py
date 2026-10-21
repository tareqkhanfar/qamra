"""The child is printed head to shoes on every layout: no box clips the bottom of the cut-out and nothing is
drawn over the shoes (owner, 2026-10-21: «جوليا»'s workbook printed her without shoes; the cut-out was the
cause, and the layouts were checked as well: the certificates' name bands and the family shopping bag sat
over the shoes of a tall figure).

Every product's pages and covers that show the child are laid out in Chromium with a tall, narrow child (the
hardest case for a box sized by height), and each cut-out `<img>` is checked at its shoes (just above the
sticker edge): the image itself is the topmost element there, and no ancestor that clips its overflow ends
above them. Pictures cropped on purpose (a passport photo, the "this is me" photo) carry `data-crop`.
"""

import asyncio
import dataclasses
import datetime as dt
from pathlib import Path
from typing import Literal

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter
from playwright.async_api import async_playwright
from qamra_workbook import islamic
from qamra_workbook.family import book_pages
from qamra_workbook.family import load as load_family
from qamra_workbook.islamic_sources import Resolver
from qamra_workbook.render.engine import book_html, build_pages
from qamra_workbook.render.family import PLAN as FAMILY_PLAN
from qamra_workbook.render.family import SAMPLES as FAMILY_SAMPLES
from qamra_workbook.render.family import plan_pages
from qamra_workbook.render.family_order import family_spec
from qamra_workbook.render.islamic_content import IslamicContext
from qamra_workbook.render.islamic_figures import kit_for
from qamra_workbook.render.islamic_volume import check_volume, volume_book
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import FamilySamples, assets_for
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import BookSpec, Child
from qamra_workbook.render.workbook import volume_specs

DAY = dt.date(2026, 10, 21)
CREAM = (248, 237, 215)
SHOES_AT = 0.965  # the shoes' row, as a share of the cut-out's height (the sticker edge is the last ~1.1 %)
TOLERANCE_PX = 1.0

FEET_JS = """
(shoes) => {
  const out = [];
  for (const img of document.querySelectorAll('img')) {
    const name = decodeURIComponent(img.src.split('/').pop());
    if (!(name in shoes) || img.closest('[data-crop]')) continue;
    const page = img.closest('[data-page]')?.dataset.page || '?';
    const where = page + ' ' + (img.className || img.parentElement.className);
    if (getComputedStyle(img).objectFit === 'cover') { out.push(where + ': object-fit cover'); continue; }
    img.scrollIntoView({block: 'center', inline: 'center'});
    const r = img.getBoundingClientRect();
    if (!r.height) continue;
    const y = r.top + r.height * SHOES_AT;
    for (let el = img.parentElement; el && el !== document.body; el = el.parentElement) {
      const cs = getComputedStyle(el);
      const clips = cs.overflow !== 'visible' || cs.overflowY !== 'visible' || cs.clipPath !== 'none';
      if (clips && el.getBoundingClientRect().bottom < y - TOLERANCE) {
        out.push(where + ': clipped by ' + el.tagName.toLowerCase() + '.' + el.className);
        break;
      }
    }
    for (const fx of shoes[name]) {
      const top = document.elementFromPoint(r.left + r.width * fx, y);
      if (top && top !== img && !img.contains(top)) {
        const cls = top.className.baseVal ?? top.className;
        out.push(where + ': shoes under ' + top.tagName.toLowerCase() + '.' + cls);
        break;
      }
    }
  }
  return out;
}
""".replace("TOLERANCE", str(TOLERANCE_PX)).replace("SHOES_AT", str(SHOES_AT))


def _tall_sheet(path: Path) -> None:
    """Three tall, narrow children (width / height about 0.24 once cut) in white sneakers on cream paper."""
    rng = np.random.default_rng(6)
    w, h = 1200, 760
    feet = h - 50
    base = np.array(CREAM, np.float32) + rng.normal(0, 0.8, (h, w, 3))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for cx in (200, 600, 1000):
        d.ellipse((cx - 56, 30, cx + 56, 150), fill=(60, 40, 30))
        d.ellipse((cx - 40, 50, cx + 40, 142), fill=(228, 180, 150))
        d.rounded_rectangle((cx - 66, 150, cx + 66, 380), radius=24, fill=(200, 70, 50))
        d.rectangle((cx - 40, 380, cx - 4, feet - 40), fill=(60, 90, 140))
        d.rectangle((cx + 4, 380, cx + 40, feet - 40), fill=(60, 90, 140))
        for x0 in (cx - 66, cx + 4):
            shoe = (x0, feet - 46, x0 + 62, feet)
            d.rounded_rectangle(shoe, radius=14, fill=(214, 204, 188), outline=(150, 140, 128), width=2)
            for k in range(3):
                d.line(
                    (x0 + 10, feet - 38 + 9 * k, x0 + 50, feet - 40 + 9 * k), fill=(165, 155, 142), width=2
                )
    img.filter(ImageFilter.GaussianBlur(0.7)).save(path)


def _shoes(assets_dir: Path) -> dict[str, list[float]]:
    """Every cut-out of the child → where its shoes are across its width (a few sample points)."""
    shoes: dict[str, list[float]] = {}
    for png in assets_dir.rglob("character-*.png"):
        with Image.open(png) as im:
            alpha = np.asarray(im.getchannel("A"))
        row = alpha[round(alpha.shape[0] * SHOES_AT)]
        cols = np.flatnonzero(row > 127)
        assert cols.size, f"no shoes on {png.name}"  # the cut-out keeps the white shoes
        picks = cols[np.linspace(0, cols.size - 1, 7).round().astype(int)[1:-1]]
        shoes[png.name] = [float(c) / alpha.shape[1] for c in picks]
    return shoes


async def _check(html: Path, shoes: dict[str, list[float]]) -> list[str]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 1600, "height": 2400})
            await page.goto(html.resolve().as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready.then(() => true)")
            problems: list[str] = await page.evaluate(FEET_JS, shoes)
            return problems
        finally:
            await browser.close()


def _laid_out(book: BookSpec, assets: Assets, out: Path) -> list[str]:
    built = build_pages(book, assets)
    pages = [p for p in built if "character-" in str(p.built.data)]
    if not pages:
        return []
    html = out / f"{book.pages[0].id}.html"
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text(book_html(book, pages, assets), encoding="utf-8")
    return asyncio.run(_check(html, _shoes(out)))


def _family(child: Child) -> BookSpec:
    samples = load_samples(FAMILY_SAMPLES)
    assert isinstance(samples, FamilySamples)
    plan = load_family(FAMILY_PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    return family_spec(tuple(specs), child, samples.family.spec(), day=DAY)


def _books(child: Child, tmp: Path) -> list[tuple[str, BookSpec]]:
    books: list[tuple[str, BookSpec]] = []
    for stage in (1, 2, 3):
        interior, cover = stage_specs(child, stage, name_en="Salma", day=DAY)
        books += [(f"journey-{stage}", interior), (f"journey-{stage}-cover", cover)]
    for level, volumes in (("kg1", (1, 2, 3)), ("kg2", (1,))):
        for number in volumes:
            interior, cover, *_ = volume_specs(child, level, number, name_en="Salma", day=DAY)
            books += [(f"{level}-{number}", interior), (f"{level}-{number}-cover", cover)]
    plan, resolver = islamic.load(), Resolver.load()
    content = check_volume(plan, "V1", resolver, build=False)
    context = IslamicContext(resolver, kit_for(child.character_sheet, tmp / "kit"), "preview", DAY)
    books.append(("islamic-1", volume_book(plan, content, context, child)))
    books.append(("family", _family(child)))
    return books


@pytest.mark.parametrize("gender", ["f", "m"])
def test_the_child_keeps_its_shoes_on_every_layout(gender: Literal["m", "f"], tmp_path: Path) -> None:
    sheet = tmp_path / "tall.png"
    _tall_sheet(sheet)
    child = Child("سلمى" if gender == "f" else "سليم", gender, sheet)
    problems: list[str] = []
    for name, book in _books(child, tmp_path):
        out = tmp_path / name
        problems += [f"{name} {p}" for p in _laid_out(book, assets_for(book, out), out)]
    assert problems == [], "\n".join(problems)


def test_the_check_sees_a_band_over_the_shoes(tmp_path: Path) -> None:
    """The check itself: a name band pulled up over the shoes (as the certificates' were) is reported, and
    the same page without it is not."""
    sheet = tmp_path / "tall.png"
    _tall_sheet(sheet)
    child = Child("سلمى", "f", sheet)
    interior, _ = stage_specs(child, 3, name_en="Salma", day=DAY)
    certificate = [p for p in interior.pages if p.type == "certificate"]
    assert certificate
    book = dataclasses.replace(interior, pages=tuple(certificate))
    out = tmp_path / "cert"
    assets = assets_for(book, out)
    assert _laid_out(book, assets, out) == []
    html = out / f"{book.pages[0].id}.html"
    band_up = "<style>.cert-name{margin-top:-14mm}</style></head>"
    broken = html.read_text(encoding="utf-8").replace("</head>", band_up)
    html.write_text(broken, encoding="utf-8")
    [problem] = asyncio.run(_check(html, _shoes(out)))
    assert "shoes under" in problem
