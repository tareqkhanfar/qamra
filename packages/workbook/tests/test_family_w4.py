"""«مغامراتي مع عائلتي» in the store (W4): an organization's logo on the back cover of its copies, and the
illustrated-family add-on's members drawn from their approved character sheets instead of the figures."""

import asyncio
import dataclasses
from pathlib import Path

from PIL import Image
from qamra_workbook.family import load
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.family import PLAN, cover_specs
from qamra_workbook.render.family_order import family_spec, with_members, with_org
from qamra_workbook.render.pages.family_cover import logo_size
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import Child, Family, Member

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "content/workbook/samples/sample-character.png"  # an AI-drawn sample sheet, not a real person
FAMILY = Family("الكيلاني", (Member("ستّي", scarf=True), Member("بابا", "سامي")), "الخليل")


def _logo(tmp: Path, size: tuple[int, int]) -> Path:
    path = tmp / "logo.png"
    Image.new("RGBA", size, "#2E9FD6").save(path)
    return path


def test_the_logo_is_never_printed_below_300_dpi(tmp_path: Path) -> None:
    w, h = logo_size(_logo(tmp_path, (300, 300)))
    assert w <= 25.4 + 0.01 and h <= 25.4 + 0.01  # a small logo stays small, but sharp
    w, h = logo_size(_logo(tmp_path, (1800, 600)))
    assert (w, h) == (44.0, 14.67)  # a big one fills its box, keeping its shape


def test_an_organizations_copies_carry_its_logo_on_the_back_cover(tmp_path: Path) -> None:
    covers = with_org(
        cover_specs(load(ROOT / PLAN)), {"name": "روضة الأمل", "logo": str(_logo(tmp_path, (900, 450)))}
    )
    book = family_spec(tuple(covers), Child("ليان", "f"), FAMILY)
    assets = Assets(LibraryStore())
    pages = build_pages(book, assets)
    back = next(p for p in pages if p.spec.type == "cover-back")
    assert back.built.data["org_name"] == "روضة الأمل" and back.built.data["org_logo"].endswith("logo.png")
    pdf = asyncio.run(
        print_pdf(book_html(book, pages, assets), tmp_path / "c.html", tmp_path / "c.pdf", book.geometry)
    )
    g = book.geometry
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed and all(c.ok for c in report.checks), report.to_dict()
    plain = build_pages(
        family_spec(tuple(cover_specs(load(ROOT / PLAN))), Child("ليان", "f"), FAMILY), assets
    )
    assert not next(p for p in plain if p.spec.type == "cover-back").built.data["org_name"]  # parents' copies


def test_approved_members_are_drawn_as_their_characters(tmp_path: Path) -> None:
    assets = with_members(Assets(LibraryStore()), {1: SHEET}, tmp_path / "assets")
    art, ratio = assets.family[1]
    assert art.exists() and 0.2 < ratio < 1
    full = family_spec(tuple(cover_specs(load(ROOT / PLAN))), Child("ليان", "f"), FAMILY)
    book = dataclasses.replace(full, pages=tuple(p for p in full.pages if p.type == "cover-front"))
    [front] = build_pages(book, assets)
    group = str(front.built.data["cv"]["group"])
    assert art.name in group  # «بابا» drawn from his sheet …
    assert (
        group.count("<image") == 1
    )  # … and «ستّي» still the placeholder figure (the child has no sheet here)
