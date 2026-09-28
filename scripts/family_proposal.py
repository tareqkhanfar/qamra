"""The «مغامراتي مع عائلتي» proposal package (Addendum 7 §3): docs/family-book/proposal.md and its PDF.

    uv run python scripts/family_proposal.py [--pdf]

The price-by-quantity table comes from the family book's `print_cost_tiers` in the store catalog (placeholders
until the printer's quote) and the margin settings, through the same pricing code the store uses. `--pdf`
also renders the designed proposal with the sample pages from out/samples/family/.
"""

import argparse
import asyncio
import base64
import html
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from qamra_workbook.family import SKILLS, FamilyPlan, book_pages, load, problems, render_markdown, shown

from qamra_core.app_settings import REGISTRY
from qamra_core.pricing import quantity_prices

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "content/family-book/plan.yaml"
CATALOG = ROOT / "content/store/catalog.yaml"
DOC = ROOT / "docs/family-book/proposal.md"
PDF = ROOT / "out/family-book/proposal.pdf"
SAMPLES = ROOT / "out/samples/family"
QUANTITIES = (1, 10, 50, 100, 500)
SKU = "family-wireo"
FOOTER = (
    '<div style="width:100%;font:8px sans-serif;color:#585C72;text-align:center">'
    'Qamra · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'
)


def setting(key: str) -> Decimal:
    return Decimal(str(REGISTRY[key].default))


def price_rows() -> tuple[list[dict[str, str]], dict[str, Any]]:
    """The price per copy by run length, with the costs it is built from (all ILS)."""
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    variant = next(v for p in catalog["products"] for v in p.get("variants", []) if v["sku"] == SKU)
    usd_ils = setting("usd_ils")
    cost = variant.get("cost", {})
    other = Decimal(str(cost.get("packaging", 0))) + Decimal(str(cost.get("handling", 0)))
    other += (Decimal(str(cost.get("ai_usd", 0))) * usd_ils).quantize(Decimal("0.01"))
    tiers = [(int(t["min_qty"]), Decimal(str(t["unit_ils"]))) for t in variant["print_cost_tiers"]]
    bulk, floor = setting("bulk_margin_pct"), setting("margin_floor_pct")
    retail = Decimal(str(variant["price"]["ILS"]))
    rows = quantity_prices(retail, tiers, other, QUANTITIES, bulk_margin_pct=bulk, floor_pct=floor)
    table = [
        {
            "Copies": str(r.qty),
            "Printer, per copy ⚠": f"{r.unit_cost - other:.2f} ₪",
            "Our cost, per copy": f"{r.unit_cost:.2f} ₪",
            "Price, per copy": f"{r.unit_price:.0f} ₪",
            "Order total": f"{r.total:,.0f} ₪",
            "Margin": f"{r.margin_pct}%",
        }
        for r in rows
    ]
    return table, {"retail": retail, "other": other, "bulk": bulk, "floor": floor, "usd_ils": usd_ils}


def write_markdown(plan: FamilyPlan) -> str:
    table, basis = price_rows()
    text = render_markdown(plan, "content/family-book/plan.yaml", table)
    note = (
        "⚠ **Placeholder printer prices.** The printer column comes from `print_cost_tiers` of "
        f"`{SKU}` in the store catalog and will be replaced by the printer's quote in the admin. "
        f"Our cost adds packaging and the character's AI cost ({basis['other']:.2f} ₪ per copy). "
        f"One copy sells at the retail price ({basis['retail']:.0f} ₪). From 10 copies, the price is the "
        f"cost plus the bulk margin ({basis['bulk']:.0f}%), rounded up to a whole shekel, never above retail "
        f"and never below the {basis['floor']:.0f}% margin floor."
    )
    text = text.replace("## 9. Price by quantity\n", f"## 9. Price by quantity\n\n{note}\n", 1)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(text, encoding="utf-8")
    return text


# ---- the designed PDF -------------------------------------------------------------------------------------


def md(text: str) -> Markup:
    """The proposal texts: paragraphs, "- " bullet lists and **bold**."""
    out, items = [], []
    for raw in [*text.strip().splitlines(), ""]:
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(raw.strip()))
        if raw.lstrip().startswith("- "):
            items.append(f"<li>{line[2:]}</li>")
            continue
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
            items = []
        if line:
            out.append(f"<p>{line}</p>")
    return Markup("\n".join(out))


CAPTIONS = {  # the rendered sample's page type → its caption in the proposal
    "section-opener": "افتتاح مغامرة «بيتي مدرسة»",
    "passport": "جواز سفر المغامر",
    "scavenger-hunt": "صيد الدوائر في المطبخ",
    "memory-page": "ذكرى اليوم",
    "shopping-list": "قائمة مشترياتي",
    "recipe-steps": "كرات اللبنة، مع صندوق الأمان",
    "feelings-thermometer": "ميزان مشاعري",
    "seven-day-challenge": "تحدي العائلة الكبير",
    "certificate-family": "شهادة المغامر",
    "badge-sticker-sheet": "ورقة الملصقات (منفصلة)",
    "play-money": "نقود قمرة للّعب (كرتون القصّ)",
}


def _images(plan: FamilyPlan, folder: Path) -> list[tuple[str, str]]:
    """(caption, data URI) per rendered sample; the opening spread first, so its two pages share a row."""
    numbers = {p.page.type: p.n for p in book_pages(plan) if any(r.n == p.n for r in plan.samples)}
    spread_first = lambda f: (not f.stem.endswith("section-opener"), f.name)  # noqa: E731
    pngs = sorted((folder / "png").glob("*.png"), key=spread_first)
    out, spread = [], 0
    for png in pngs:
        kind = png.stem.split("-", 1)[-1]
        n = numbers.get(kind)
        if kind == "section-opener":
            n, spread = (n or 0) + spread, spread + 1
        caption = CAPTIONS.get(kind, kind) + (f" · ص {n}" if n else "")
        out.append((caption, "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()))
    return out


async def write_pdf(plan: FamilyPlan) -> Path:
    from qamra_pdf import html_to_pdf

    env = Environment(
        loader=FileSystemLoader(ROOT / "scripts/templates"), autoescape=select_autoescape(["html", "j2"])
    )
    env.filters["md"] = md
    env.filters["shown"] = shown
    pages = book_pages(plan)
    table, basis = price_rows()
    html = env.get_template("family-proposal.html.j2").render(
        plan=plan,
        pages=pages,
        counts=Counter(p.section for p in pages),
        skills=SKILLS,
        table=table,
        basis=basis,
        samples=_images(plan, SAMPLES),
        fonts=(ROOT / "packages/pdf/src/qamra_pdf/fonts").as_uri(),
    )
    PDF.parent.mkdir(parents=True, exist_ok=True)
    return await html_to_pdf(html, PDF, footer=FOOTER)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true", help="also render the designed proposal PDF")
    args = parser.parse_args()
    plan = load(PLAN)
    found = problems(plan)
    if found:
        print("\n".join(f"✗ {f}" for f in found))
        return 1
    write_markdown(plan)
    print("wrote", DOC.relative_to(ROOT))
    if args.pdf:
        print("wrote", asyncio.run(write_pdf(plan)).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
