"""The «قلبي يعرف الله» proposal package (Addendum 10 §4): docs/islamic/proposal.md and its designed PDF.

    uv run python scripts/islamic_proposal.py [--pdf]

Everything is generated from content/islamic/ (plan, units, concepts, volumes, sources,
proposal-text.yaml). The page numbers, counts and the retention matrix are computed from the plan itself,
so the document cannot say what the plan does not. `--pdf` also renders the designed proposal with the
sample pages of out/samples/islamic/png/.
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
from qamra_workbook.islamic import FORMS, Plan, coverage, load, problems, unused_sources, weak_concepts

from qamra_core.app_settings import REGISTRY
from qamra_core.pricing import quantity_prices

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content/islamic"
DOC = ROOT / "docs/islamic/proposal.md"
PDF = ROOT / "out/islamic/proposal.pdf"
SAMPLES = ROOT / "out/samples/islamic"
QUANTITIES = (1, 10, 50, 100, 500)
# ⚠ placeholders until the printer's quote: perfect-bound softcover, 21×28, ~112 colour pages, 140 gsm
PRINT_TIERS = [
    (1, Decimal("40")),
    (10, Decimal("35")),
    (50, Decimal("29")),
    (100, Decimal("25")),
    (500, Decimal("18")),
]
PACKAGING = Decimal("3")
AI_USD = Decimal("0.30")
RETAIL = Decimal("79")
DIGITAL = Decimal("35")
SETS = [
    ("مجموعة المستوى الأول (المجلدان 1–2)", ("V1", "V2"), Decimal("139")),
    ("مجموعة المستوى الثاني (المجلدات 3–5)", ("V3", "V4", "V5"), Decimal("199")),
    ("المجموعة الكاملة (5 مجلدات)", ("V1", "V2", "V3", "V4", "V5"), Decimal("329")),
]
FOOTER = (
    '<div style="width:100%;font:8px sans-serif;color:#585C72;text-align:center">'
    'Qamra · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'
)
TYPE_AR = {  # page type → short Arabic label for the TOC
    "story": "قصة",
    "prophet-story": "قصة نبي",
    "sira-story": "من السيرة",
    "pillar-card": "بطاقة ركن",
    "coloring": "تلوين",
    "maze": "متاهة",
    "find-objects": "بحث",
    "blessings-hunt": "بحث عن النعم",
    "order-steps": "ترتيب الخطوات",
    "match": "وصل",
    "draw": "رسم",
    "surah": "سورة",
    "true-false": "صح أو خطأ",
    "choose": "اختيار",
    "dhikr": "ذكر وموقف",
    "wwyd": "ماذا كنت ستفعل؟",
    "wdif": "ماذا أفعل لو؟",
    "role-play": "تمثيل",
    "day": "يومي مع الله",
    "self-test": "اختبر نفسك",
    "assessment": "تقييم",
}


def setting(key: str) -> Decimal:
    return Decimal(str(REGISTRY[key].default))


def ranges(ns: list[int]) -> str:
    """3, 7–9, 12 from sorted page numbers."""
    out, i = [], 0
    ns = sorted(set(ns))
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(str(ns[i]) if i == j else f"{ns[i]}–{ns[j]}")
        i = j + 1
    return "، ".join(out)


def md(text: str) -> Markup:
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


def price_rows() -> tuple[list[dict[str, str]], dict[str, Any], list[dict[str, str]]]:
    usd_ils = setting("usd_ils")
    other = PACKAGING + (AI_USD * usd_ils).quantize(Decimal("0.01"))
    bulk, floor = setting("bulk_margin_pct"), setting("margin_floor_pct")
    rows = quantity_prices(RETAIL, PRINT_TIERS, other, QUANTITIES, bulk_margin_pct=bulk, floor_pct=floor)
    table = [
        {
            "copies": str(r.qty),
            "printer": f"{r.unit_cost - other:.2f}",
            "cost": f"{r.unit_cost:.2f}",
            "price": f"{r.unit_price:.0f}",
            "total": f"{r.total:,.0f}",
            "margin": f"{r.margin_pct}",
        }
        for r in rows
    ]
    one = rows[0].unit_cost
    sets = []
    for name, vols, price in SETS:
        cost = one * len(vols)
        sets.append(
            {
                "name": name,
                "price": f"{price:.0f}",
                "separate": f"{RETAIL * len(vols):.0f}",
                "saving": f"{(1 - price / (RETAIL * len(vols))) * 100:.0f}",
                "margin": f"{(price - cost) / price * 100:.0f}",
            }
        )
    return table, {"other": other, "bulk": bulk, "floor": floor, "usd_ils": usd_ils}, sets


def context() -> dict[str, Any]:
    plan: Plan = load()
    text = yaml.safe_load((CONTENT / "proposal-text.yaml").read_text(encoding="utf-8"))
    samples = yaml.safe_load((CONTENT / "samples.yaml").read_text(encoding="utf-8"))["pages"]
    cov = coverage(plan)
    volumes = []
    for vid, v in plan.volumes.items():
        pages = plan.pages[vid]
        units = []
        for u in v["units"]:
            mine = [p for p in pages if p.unit == u["id"]]
            lessons = []
            for i, les in enumerate(u["lessons"], 1):
                ln = [p.n for p in mine if p.kind == "lesson" and p.lesson == i]
                lessons.append(
                    {
                        "title": les["t"],
                        "pages": ranges(ln),
                        "count": len(ln),
                        "kinds": "، ".join(dict.fromkeys(TYPE_AR.get(t, t) for t in les["p"])),
                    }
                )
            ident = plan.units[u["id"]]
            units.append(
                {
                    "id": u["id"],
                    "title": ident["title_ar"],
                    "color": ident["color"],
                    "icon": ident["icon"],
                    "pages": f"{mine[0].n}–{mine[-1].n}",
                    "count": len(mine),
                    "lessons": lessons,
                }
            )
        first: dict[str, int] = {}
        for p in pages:
            for c in p.concepts:
                first.setdefault(c, p.n)
        matrix = []
        for c in sorted(first, key=lambda c: first[c]):
            if c not in plan.concepts:
                continue
            cells = {}
            for f in FORMS:
                ns = [p.n for p in pages if c in p.concepts and f in p.forms]
                cells[f] = ranges(ns[:6]) + (" …" if len(ns) > 6 else "") if ns else ""
            matrix.append(
                {
                    "id": c,
                    "ar": plan.concepts[c]["ar"],
                    "cells": cells,
                    "forms": sum(1 for f in FORMS if cells[f]),
                }
            )
        used = {s for p in pages for s in p.sources}
        extras = Counter(p.kind for p in pages)
        volumes.append(
            {
                "id": vid,
                "title": v["title_ar"],
                "title_en": v["title_en"],
                "level": v["level"],
                "age": v["age"],
                "goal": v["goal"],
                "pages": len(pages),
                "units": units,
                "matrix": matrix,
                "sources": len(used),
                "parent_pages": extras["parent"],
                "closing_pages": extras["closing"],
                "cumulative_pages": extras["cumulative"],
                "front_pages": extras["front"],
                "back_pages": extras["back"],
                "lessons": sum(len(u["lessons"]) for u in v["units"]),
                "concepts": len({c for p in pages for c in p.concepts if c in plan.concepts}),
            }
        )
    kinds = Counter(s["kind"] for s in plan.sources.values())
    decisions = [
        {"id": sid, "title": s.get("title_ar", sid), "q": s["scholar_decision"], "kind": s["kind"]}
        for sid, s in plan.sources.items()
        if s.get("scholar_decision")
    ]
    table, basis, sets = price_rows()
    images = []
    for s in samples:
        png = SAMPLES / "png" / f"{s['id']}.png"
        images.append(
            {
                "id": s["id"],
                "type": s.get("engine_type") or s["type"],
                "title": re.sub(r"\{[^{}/]*/([^{}]*)\}", r"\1", s["title"]),  # the sample child is a girl
                "unit": plan.units.get(s.get("unit", ""), {}).get("title_ar", ""),
                "path": png if png.exists() else None,
            }
        )
    return {
        "plan": plan,
        "text": text,
        "series": plan.series,
        "volumes": volumes,
        "characters": plan.characters,
        "units": [plan.units[u] for u in plan.units],
        "page_types": plan.page_types,
        "endings": plan.endings,
        "forms": text["retention"]["forms"],
        "kinds": kinds,
        "decisions": decisions,
        "samples": images,
        "unused": unused_sources(plan),
        "weak": weak_concepts(plan),
        "concepts": len(plan.concepts),
        "five": sum(1 for c in cov.values() if sum(1 for f in FORMS if c["forms"][f]) == 5),
        "six": sum(1 for c in cov.values() if all(c["forms"][f] for f in FORMS)),
        "total_pages": sum(v["pages"] for v in volumes),
        "price": table,
        "basis": basis,
        "sets": sets,
        "retail": RETAIL,
        "digital": DIGITAL,
        "tiers": PRINT_TIERS,
        "sources_total": len(plan.sources),
    }


# ---- markdown ---------------------------------------------------------------------------------------------


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def write_markdown(c: dict[str, Any]) -> str:
    t, s = c["text"], c["series"]
    o: list[str] = []
    o.append(f"# {s['working_title']} — Islamic education series (proposal package)\n")
    o.append(
        "Proposal package (Addendum 10 §4). Generated from `content/islamic/`; edit the YAML, not this file. "
        "**AI-drafted: nothing here is religiously final until the scholar signs it off.**\n"
    )
    o.append("## 1. الفكرة والرؤية\n")
    o += [p + "\n" for p in t["concept"]["paragraphs"]]
    o.append("**ما يميّزها:**\n\n" + bullets(t["concept"]["differentiators"]) + "\n")
    o.append("### خمسة أسماء مقترحة (والاسم المبدئي «قلبي يعرف الله»)\n")
    o.append("| الاسم | لماذا | ملاحظة |\n|---|---|---|")
    for n in s["names"]:
        o.append(f"| {n['ar']} | {n['why']} | {n['watch']} |")
    o.append("\n## 2. تقسيم السلسلة\n")
    o.append(t["split"]["intro"] + "\n")
    o.append(
        "| المجلد | المستوى | العمر | العنوان | الصفحات | الوحدات | الدروس |\n|---|---|---|---|---|---|---|"
    )
    for v in c["volumes"]:
        lvl = "موسمي" if v["level"] == 0 else f"المستوى {'الأول' if v['level'] == 1 else 'الثاني'}"
        o.append(
            f"| {v['id']} | {lvl} | {v['age'][0]}–{v['age'][1]} | {v['title']} | {v['pages']} | "
            f"{len(v['units'])} | {v['lessons']} |"
        )
    o.append(f"\nالمجموع: **{c['total_pages']} صفحة** في ستة كتب.\n")
    o.append(bullets(t["split"]["why"]) + "\n")
    o += [t["split"]["alternative"] + "\n", t["split"]["seasonal"] + "\n"]
    o.append("### ما يغطّيه كل مجلد\n")
    for v in c["volumes"]:
        o.append(f"- **{v['id']} · {v['title']}:** {v['goal']}")
    o.append("\n## 3. الفهرس الكامل\n")
    o.append(
        "لكل وحدة تلقائيًا: صفحة افتتاح، ثم الدروس، ثم صفحتا الخاتمة، ثم صفحة الأهل. "
        "أرقام الصفحات محسوبة من الخطة.\n"
    )
    for v in c["volumes"]:
        o.append(f"### {v['id']} · {v['title']} — {v['pages']} صفحة\n")
        o.append(
            f"صفحات البداية: {v['front_pages']} · وحدات: {len(v['units'])} · "
            f"مراجعات تراكمية: {v['cumulative_pages']} · الخاتمة (تقييم وجواز وشهادة): {v['back_pages']}\n"
        )
        o.append("| الوحدة | الصفحات | العدد | الدروس (صفحاتها: أنواعها) |\n|---|---|---|---|")
        for u in v["units"]:
            les = "؛ ".join(f"{x['title']} ({x['pages']}: {x['kinds']})" for x in u["lessons"])
            o.append(f"| {u['title']} | {u['pages']} | {u['count']} | {les} |")
        o.append("")
    o.append("## 4. نظام التثبيت\n")
    o.append(t["retention"]["intro"] + "\n")
    o.append("| الشكل | ما هو |\n|---|---|")
    for f in t["retention"]["forms"]:
        o.append(f"| {f['ar']} | {f['d']} |")
    o.append("\n" + bullets(t["retention"]["rules"]) + "\n")
    o.append(
        f"**النتيجة:** {c['concepts']} مفهومًا أساسيًا في السلسلة: {c['six']} منها يصل إلى الأشكال الستة، "
        f"و{c['five']} إلى خمسة؛ ولا مفهوم أقل من ذلك (فحص بناء الخطة).\n"
    )
    o.append(t["retention"]["how_to_read"] + "\n")
    names = {f["k"]: f["ar"] for f in t["retention"]["forms"]}
    for v in c["volumes"]:
        o.append(f"### مصفوفة {v['id']} · {v['title']}\n")
        o.append("| المفهوم | " + " | ".join(names[f] for f in FORMS) + " |\n|---|" + "---|" * len(FORMS))
        for m in v["matrix"]:
            o.append(f"| {m['ar']} | " + " | ".join(m["cells"][f] or "·" for f in FORMS) + " |")
        o.append("")
    o.append("## 5. خاتمة الوحدة وصفحات الأهل\n")
    o.append(t["closing"]["intro"] + "\n")
    o.append(bullets(t["closing"]["items"]) + "\n")
    o.append(t["closing"]["placement"] + "\n")
    o.append("## 6. الشخصيات المتكرّرة\n")
    for ch in c["characters"]:
        o.append(f"- **{ch['ar']}** — {ch['role']}. *{ch['note']}*")
    o.append("\n" + t["characters_note"] + "\n")
    o.append("## 7. الهوية البصرية لكل وحدة\n")
    o.append(t["identity_note"] + "\n")
    o.append("| الوحدة | المجلد | اللون | الرمز | الزخرفة |\n|---|---|---|---|---|")
    for u in c["units"]:
        o.append(f"| {u['title_ar']} | {u['volume']} | `{u['color']}` | {u['icon']} | {u['motif']} |")
    o.append("\n## 8. اثنتا عشرة صفحة نموذجية\n")
    o.append(t["samples_note"] + "\n")
    for sm in c["samples"]:
        if sm["path"]:
            rel = Path("../..") / sm["path"].relative_to(ROOT)
            o.append(f"**{sm['title']}** ({sm['type']}، {sm['unit']})\n\n![{sm['title']}]({rel})\n")
        else:
            o.append(f"- **{sm['title']}** ({sm['type']}، {sm['unit']}): قيد التصميم")
    o.append("\n## 9. قائمة المصادر للمشرف العلمي\n")
    o.append(t["sources"]["intro"] + "\n")
    k = c["kinds"]
    o.append(
        f"المجموع **{c['sources_total']} مرجعًا**: {k['quran']} مقطعًا قرآنيًا، {k['hadith']} حديثًا، "
        f"{k['dua']} ذكرًا ودعاءً، {k['sira']} من السيرة، {k['ruling']} من الأحكام المبسّطة. "
        "القائمة المقروءة بنصوصها المرشّحة وخانات الاعتماد: `out/islamic/sources-for-scholar.pdf`.\n"
    )
    o.append(bullets(t["sources"]["how"]) + "\n")
    o.append("### قرارات للمشرف (تُرفع إلى طابور المراجعة)\n")
    o.append(f"{len(c['decisions'])} نقطة اختلاف أو حساسية، ولا يُختار فيها مذهب بصمت:\n")
    o.append("| المصدر | السؤال |\n|---|---|")
    for d in c["decisions"]:
        o.append(f"| {d['title']} (`{d['id']}`) | {d['q']} |")
    o.append("\n### ما لن نستعمله\n")
    o.append(t["sources"]["excluded_intro"] + "\n")
    o.append(bullets(t["sources"]["excluded"]) + "\n")
    if c["unused"]:
        o.append(
            "مراجع في السجلّ ولا يستعملها أي درس الآن (للاستعمال لاحقًا أو للحذف): "
            + "، ".join(f"`{u}`" for u in c["unused"])
            + ".\n"
        )
    o.append("## 10. الحجم والورق والتجليد والأسعار\n")
    o += [t["print"]["size"] + "\n", t["print"]["paper"] + "\n", t["print"]["binding_intro"] + "\n"]
    o.append("| الخيار | المزايا | العيوب |\n|---|---|---|")
    for b in t["print"]["bindings"]:
        o.append(f"| {b['name']} | {b['pros']} | {b['cons']} |")
    o.append("\n" + t["print"]["recommendation"] + "\n")
    o.append(t["print"]["product_note"] + "\n")
    o.append("### سعر المجلد حسب الكمية\n")
    basis = c["basis"]
    o.append(
        "⚠ **أسعار طباعة مؤقتة** (عمود الطابعة تقدير لغلاف ورقي لاصق 21×28، "
        "نحو 112 صفحة ملوّنة 140 غرام) حتى عرض المطبعة. تكلفتنا تضيف التغليف وكلفة الذكاء الاصطناعي "
        f"لشخصية الطفل ({basis['other']:.2f} ₪ للنسخة). "
        f"نسخة واحدة بسعر {c['retail']:.0f} ₪، ومن 10 نسخ السعر = التكلفة + هامش الجملة "
        f"({basis['bulk']:.0f}%) مقرّبًا لشيكل صحيح، لا فوق سعر المفرّق ولا تحت حدّ الهامش "
        f"({basis['floor']:.0f}%).\n"
    )
    o.append(
        "| النسخ | الطابعة ⚠ | تكلفتنا | السعر للنسخة | إجمالي الطلب | الهامش % |\n|---|---|---|---|---|---|"
    )
    for r in c["price"]:
        cells = [r["copies"], f"{r['printer']} ₪", f"{r['cost']} ₪", f"{r['price']} ₪"]
        cells += [f"{r['total']} ₪", r["margin"]]
        o.append("| " + " | ".join(str(x) for x in cells) + " |")
    o.append(f"\nالنسخة الرقمية PDF: {c['digital']:.0f} ₪.\n")
    o.append("| المجموعة | سعرها | مجموع الأسعار منفصلة | التوفير % | الهامش % |\n|---|---|---|---|---|")
    for st in c["sets"]:
        o.append(f"| {st['name']} | {st['price']} ₪ | {st['separate']} ₪ | {st['saving']} | {st['margin']} |")
    o.append("\n" + t["print"]["prices_note"] + "\n")
    o.append("## 11. القرارات المطلوبة منك والخطوات التالية\n")
    o.append("| القرار | توصيتي |\n|---|---|")
    for d in t["decisions"]:
        o.append(f"| {d['q']} | {d['a']} |")
    o.append("\n### ترتيب العمل والمدد التقريبية\n")
    o.append("| الخطوة | ما فيها | المدة |\n|---|---|---|")
    for st in t["timeline"]:
        o.append(f"| {st['step']} | {st['what']} | {st['when']} |")
    text = "\n".join(o) + "\n"
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(text, encoding="utf-8")
    return text


# ---- the designed PDF ------------------------------------------------------------


def _uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


async def write_pdf(c: dict[str, Any]) -> Path:
    from qamra_pdf import html_to_pdf

    env = Environment(
        loader=FileSystemLoader(ROOT / "scripts/templates"), autoescape=select_autoescape(["html", "j2"])
    )
    env.filters["md"] = md
    samples = [{**s, "src": _uri(s["path"]) if s["path"] else None} for s in c["samples"]]
    page = env.get_template("islamic-proposal.html.j2").render(
        **{**c, "samples": samples},
        fonts=(ROOT / "packages/pdf/src/qamra_pdf/fonts").as_uri(),
        names={f["k"]: f["ar"] for f in c["text"]["retention"]["forms"]},
        FORMS=FORMS,
    )
    PDF.parent.mkdir(parents=True, exist_ok=True)
    return await html_to_pdf(page, PDF, footer=FOOTER)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="also render the designed proposal PDF")
    args = ap.parse_args()
    ctx = context()
    found = problems(ctx["plan"])
    if found:
        print("\n".join(f"✗ {f}" for f in found))
        return 1
    write_markdown(ctx)
    print("wrote", DOC.relative_to(ROOT))
    if args.pdf:
        print("wrote", asyncio.run(write_pdf(ctx)).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
