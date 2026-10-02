"""Sample book end to end: photo (+ drawing) → character → story → pages → print PDFs, preflight, cost.

Addendum 3 acceptance runs use this (or the admin's /admin/samples page, which runs the same pipeline).

Examples:
  # offline, $0, design-style placeholder art (no keys needed):
  uv run scripts/sample_book.py --theme first-day --name "سلمى" --gender f --age 5 --hijab --provider sketch
  # real providers (keys from .env): Nano Banana 2 on fal + Sonnet 5 + Haiku 4.5
  uv run scripts/sample_book.py --photo kid.jpg --name "سلمى" --gender f --age 5 --theme first-day
  # with the child's drawing as companion:
  uv run scripts/sample_book.py ... --drawing drawing.jpg --companion-name "بوبو"
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

from qamra_ai.config import Settings
from qamra_ai.errors import QamraError
from qamra_ai.image import make_image_provider, make_upscaler
from qamra_ai.pipeline.assemble import AssemblyInputs, assemble_book
from qamra_ai.pipeline.book import BookInputs, BookRun, default_companion, run_book
from qamra_ai.pipeline.budget import Budget
from qamra_ai.pipeline.character import generate_character_sheet
from qamra_ai.pipeline.companion import generate_companion_options
from qamra_ai.pipeline.drawing import clean_drawing
from qamra_ai.pipeline.models import Child, CompanionSpec
from qamra_ai.pipeline.photo_check import check_photo
from qamra_ai.pipeline.plates import DirPlateStore
from qamra_ai.pipeline.projection import project
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_style, load_theme
from qamra_ai.text import make_text_provider
from qamra_pdf import Brand

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHOTO = ROOT / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--photo", type=Path, action="append", help="child photo (repeat up to 3 times)")
    p.add_argument("--name", required=True)
    p.add_argument("--gender", choices=["m", "f"], required=True)
    p.add_argument("--age", type=int, required=True)
    p.add_argument("--hijab", action="store_true", help="the parent chose a hijab")
    p.add_argument("--glasses", action="store_true")
    p.add_argument("--interests", default="", help="comma-separated")
    p.add_argument("--theme", default="first-day")
    p.add_argument("--style", default="watercolor")
    p.add_argument("--lang", choices=["ar", "en"], default="ar")
    p.add_argument("--provider", choices=["fal", "gemini", "openai", "sketch", "fake"], default=None)
    p.add_argument("--mode", choices=["final", "preview"], default="final")
    p.add_argument("--message", help="the parent's dedication message (≤ 120 characters)")
    p.add_argument("--drawing", type=Path, help="photo of the child's drawing (companion)")
    p.add_argument("--companion-name")
    p.add_argument("--companion-type", choices=["creature", "animal", "robot", "other"], default="creature")
    p.add_argument("--qr-url", help="URL for the back-cover QR code (family voice)")
    p.add_argument(
        "--cover-thumbs",
        action="store_true",
        help="also write cover-thumbs.png: the front in every title treatment at 300 × 300 px",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", type=Path, default=ROOT / "out")
    return p.parse_args(argv)


def _secret_set(settings: Settings, name: str) -> bool:
    return getattr(settings, name) is not None


def write_report(
    out: Path, args: argparse.Namespace, rt: Runtime, run: BookRun, files: object, seconds: float
) -> dict[str, object]:
    from qamra_ai.pipeline.assemble import BookFiles

    assert isinstance(files, BookFiles)  # nosec B101
    projection = project(rt.ledger, rt.settings)
    story_pages = run.plan.beats
    rows = []
    for beat, res in sorted(run.pages.items()):
        plan = story_pages[beat]
        rows.append(
            f"| {plan.page_label} | {plan.layout} | {res.status} | {len(res.attempts)} | "
            f"{'' if res.score is None else f'{res.score:.2f}'} | "
            f"{'' if res.qa is None else res.qa.likeness} | {', '.join(res.flags) or '—'} |"
        )
    judged = [r for r in run.pages.values() if r.qa is not None and not story_pages[r.beat].no_child]
    recognizable = sum(r.qa.likeness >= 7 for r in judged if r.qa) / len(judged) if judged else 0.0
    attempts = sum(len(r.attempts) for r in run.pages.values())
    redraws = sum(r.redraws for r in run.pages.values())
    s = rt.settings
    n = len(run.pages)
    lines = [
        f"# Sample book — {args.name} · {args.theme} · {args.lang} · {args.mode}",
        "",
        f"- providers: images **{rt.image.name} / {rt.image.model}**, "
        f"upscaler **{rt.upscaler.name} / {rt.upscaler.model}**, "
        f"text **{rt.text.name}** (story `{s.text_model}`, checks `{s.text_model_fast}`)",
        f"- pages: {run.plan.page_count} interior pages (+ cover wrap); {n} illustrations; "
        f"status {run.status_counts()}; book flags: {', '.join(run.flags) or '—'}",
        f"- regeneration rate: {redraws} redraws / {n} illustrations = {redraws / max(1, n):.0%}"
        f" ({attempts} image calls)",
        f"- child recognizable (QA likeness ≥ 7/10): **{recognizable:.0%}** of pages with the hero"
        " (target ≥ 90%)",
        f"- wall time: {seconds:.0f}s",
        "",
        "## Print files",
    ]
    for name, report in files.preflight.items():
        verdict = "PASS" if report.passed else "FAIL"
        lines.append(f"- `{name}.pdf`: preflight **{verdict}** (min image DPI {report.min_dpi})")
        lines += [
            f"  - {'✓' if c.ok else ('⚠' if c.level == 'warning' else '✗')} {c.name}: {c.detail}"
            for c in report.checks
        ]
    if files.proof_pdf:
        lines.append(f"- `proof.pdf`: low-res web proof ({files.proof_pdf.stat().st_size / 1e6:.1f} MB)")
    page_flags = {k: v for k, v in files.flags.items() if v}
    if page_flags:
        lines.append(f"- layout flags: {json.dumps(page_flags, ensure_ascii=False)}")
    groups = ", ".join(f"{k} ${v:.3f}" for k, v in rt.ledger.by_group().items()) or "offline"
    lines += [
        "",
        "## Cost",
        f"- this run: **${rt.ledger.total_usd:.3f}** ({groups})",
        f"- same run on the default paid stack (fal `{s.fal_image_model}` {s.final_resolution} + "
        f"`{s.fal_upscale_model}`, `{s.text_model}`, `{s.text_model_fast}`): "
        f"**${projection.total:.2f}**",
        "",
        "| line | calls | USD |",
        "|---|---|---|",
        *(f"| {k} | {projection.counts[k]} | {v:.4f} |" for k, v in sorted(projection.lines.items())),
        "",
        "Image and upscale lines use verified list prices; Claude lines use typical token counts until real"
        " usage exists.",
        "",
        "## Pages",
        "| page | layout | status | attempts | QA score | likeness | flags |",
        "|---|---|---|---|---|---|---|",
        *rows,
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "actual_usd": rt.ledger.total_usd,
        "projected_usd": projection.total,
        "projection": dict(projection.lines),
        "recognizable": recognizable,
        "redraws": redraws,
        "illustrations": len(run.pages),
        "preflight": {k: v.to_dict() for k, v in files.preflight.items()},
        "flags": run.flags,
    }
    (out / "report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "cost.json").write_text(
        json.dumps(rt.ledger.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    provider = args.provider or settings.image_provider
    offline = provider in ("sketch", "fake")
    settings = settings.model_copy(
        update={"image_provider": provider, **({"text_provider": "fake"} if offline else {})}
    )
    photos = [p.read_bytes() for p in (args.photo or ([DEFAULT_PHOTO] if offline else []))]
    if not photos:
        print("--photo is required with a real provider")
        return 2
    if not offline:
        for path, c in zip(args.photo, (check_photo(b) for b in photos), strict=True):
            if not c.ok:
                print(f"✗ {path.name}: " + "; ".join(i.message_en for i in c.issues))
                return 2

    theme, style = load_theme(args.theme), load_style(args.style)
    child = Child(
        name=args.name,
        gender=args.gender,
        age=args.age,
        hijab=args.hijab,
        glasses=args.glasses,
        interests=[s.strip() for s in args.interests.split(",") if s.strip()],
    )
    out = (args.out / f"{time.strftime('%Y%m%d-%H%M%S')}-{provider}-{args.theme}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    print(f"→ {out}")

    image = make_image_provider(settings)
    rt_child = Runtime(
        settings=settings, text=make_text_provider(settings), image=image, upscaler=make_upscaler(settings)
    )
    started = time.monotonic()
    try:
        sheet = await generate_character_sheet(rt_child, child, photos, style)
        (out / "character-sheet.png").write_bytes(sheet.data)
        companion: CompanionSpec | None = default_companion(theme, args.lang)
        companion_sheet: bytes | None = None
        drawing: bytes | None = None
        if args.drawing:
            cleaned = clean_drawing(args.drawing.read_bytes())
            drawing = cleaned.png
            spec = CompanionSpec(name=args.companion_name or "صاحبي", type_hint=args.companion_type)
            options = await generate_companion_options(rt_child, drawing, spec, style)
            companion, companion_sheet = options.spec, options.options[0].data
            (out / "companion-sheet.png").write_bytes(companion_sheet)

        rt = Runtime(
            settings=settings,
            text=rt_child.text,
            image=image,
            upscaler=rt_child.upscaler,
            budget=Budget(cap_usd=settings.book_budget_usd),
        )
        inputs = BookInputs(
            child=child,
            lang=args.lang,
            theme=theme,
            style=style,
            character_sheet=sheet.data,
            companion=companion,
            companion_sheet=companion_sheet,
            has_drawing=drawing is not None,
            parent_message=args.message,
            seed=args.seed,
            plates=DirPlateStore(args.out / "plate-cache"),
        )
        book = await run_book(rt, inputs, mode=args.mode)
        if book.story is None:
            print(f"✗ stopped before the story: {book.flags}")
            return 1
        (out / "story.json").write_text(book.story.out.model_dump_json(indent=2), encoding="utf-8")
        s = settings
        files = await assemble_book(
            AssemblyInputs(
                run=book,
                story=book.story.out,
                child=child,
                lang=args.lang,
                brand=Brand(
                    s.brand_name_ar, s.brand_name_en, s.brand_domain, s.brand_tagline_ar, s.brand_tagline_en
                ),
                character_sheet=sheet.data,
                parent_message=args.message,
                companion_name=companion.name if companion else None,
                drawing=drawing,
                companion_sheet=companion_sheet,
                qr_url=args.qr_url,
                made_on=date.today(),
                watermark=args.mode == "preview",
            ),
            out,
            print_files=args.mode == "final",
        )
        if args.cover_thumbs:
            from qamra_pdf.thumbs import cover_thumbs

            await cover_thumbs(files.spec, out / "cover-thumbs.png")
    except QamraError as e:
        print(f"✗ {type(e).__name__}: {e}")
        return 1
    finally:
        close = getattr(image.primary, "aclose", None)
        if close:
            await close()
    rt.ledger.entries[:0] = rt_child.ledger.entries  # one report for the whole run
    summary = write_report(out, args, rt, book, files, time.monotonic() - started)
    verdict = "PASS" if files.preflight_passed else ("n/a" if not files.preflight else "FAIL")
    print(
        f"✓ {book.plan.page_count} pages · preflight {verdict} · actual ${summary['actual_usd']:.3f}"
        f" · projected ${summary['projected_usd']:.2f} → {out / 'report.md'}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(run(parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
