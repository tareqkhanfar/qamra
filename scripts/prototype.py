"""Phase 0 prototype: photo (+ optional drawing) → character → story → pages → print PDFs + cost report.

Examples:
  uv run scripts/prototype.py --photo kid.jpg --name "سلمى" --gender f --age 5 \\
      --theme first-day --style watercolor --lang ar --provider gemini
  uv run scripts/prototype.py ... --drawing drawing.jpg --companion-name "بوبو" --companion-type creature
  uv run scripts/prototype.py ... --provider fake          # offline dry run, $0
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

from qamra_ai.config import get_settings
from qamra_ai.errors import QamraError
from qamra_ai.image import make_image_provider
from qamra_ai.image.base import GeneratedImage
from qamra_ai.pipeline.book import BookArtifacts, BookRequest, generate_book
from qamra_ai.pipeline.drawing import clean_drawing
from qamra_ai.pipeline.models import Child, CompanionSpec
from qamra_ai.pipeline.photo_check import check_photo
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_style, load_theme
from qamra_ai.pipeline.upscale import print_px, to_jpeg, to_print_jpeg
from qamra_ai.text import make_text_provider
from qamra_pdf import BookSpec, Brand, KeepsakeSpec, PageSpec, render_book

ROOT = Path(__file__).resolve().parents[1]
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument(
        "--photo",
        type=Path,
        action="append",
        required=True,
        help="child photo (repeat up to 3 times)",
    )
    p.add_argument("--name", required=True)
    p.add_argument("--gender", choices=["m", "f"], required=True)
    p.add_argument("--age", type=int, required=True)
    p.add_argument("--interests", default="", help="comma-separated, e.g. 'dinosaurs,drawing'")
    p.add_argument("--theme", default="first-day")
    p.add_argument("--style", default="watercolor")
    p.add_argument("--lang", choices=["ar", "en"], default="ar")
    p.add_argument(
        "--provider",
        choices=["gemini", "flux", "openai", "fake"],
        default=None,
        help="image provider (default: IMAGE_PROVIDER from .env)",
    )
    p.add_argument("--drawing", type=Path, help="photo of the child's drawing (companion)")
    p.add_argument("--companion-name")
    p.add_argument("--companion-type", choices=["creature", "animal", "robot", "other"], default="creature")
    p.add_argument("--companion-other", help="free text when --companion-type other (≤ 30 chars)")
    p.add_argument("--companion-traits")
    p.add_argument("--companion-pick", type=int, choices=[1, 2], default=1)
    p.add_argument("--preview", action="store_true", help="watermark pages (preview copy)")
    p.add_argument("--skip-photo-check", action="store_true")
    p.add_argument("--out", type=Path, default=ROOT / "out")
    return p.parse_args()


def save(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def save_image(dir_: Path, stem: str, img: GeneratedImage) -> Path:
    return save(dir_ / f"{stem}.{EXT.get(img.mime, 'png')}", img.data)


def write_report(
    out: Path,
    args: argparse.Namespace,
    book: BookArtifacts,
    rt: Runtime,
    seconds: float,
    photo_metrics: dict[str, float],
) -> None:
    ledger = rt.ledger
    n = len(book.pages)
    pages_rows = []
    for p in [book.cover, *book.pages]:
        label = "cover" if p.index == 0 else str(p.index)
        r = p.review
        pages_rows.append(
            f"| {label} | {p.status} | {p.attempts} | "
            f"{'✓' if r and r.hero_recognizable else '✗'} | "
            f"{'✓' if r and r.companion_present else '✗'} | "
            f"{'✗' if r and r.has_text_artifacts else '✓'} | {(r.notes if r else '')[:80]} |"
        )
    fid = book.companion_fidelity
    per_page = ledger.total_usd / n if n else 0
    lines = [
        f"# Prototype run — {args.name} · {args.theme} · {args.style} · {args.lang}",
        "",
        f"- image provider: **{rt.image.name} / {rt.image.model}**; text: **{rt.text.name}**",
        f"- wall time: {seconds:.0f}s",
        f"- photo check: {json.dumps(photo_metrics, ensure_ascii=False)}",
        f"- recognizable (after auto-redraw): **{book.recognizable_ratio:.0%}** of {n} pages "
        f"(first attempt: {book.first_attempt_recognizable_ratio:.0%}) — target ≥ 80%",
    ]
    if book.companion:
        lines.append(
            f"- companion: {book.companion.name} "
            f"({'from drawing' if book.companion.from_drawing else 'theme default'})"
        )
    if fid:
        lines.append(
            f"- companion fidelity: **{fid.score}/5**; kept: {', '.join(fid.preserved_features)}; "
            f"lost: {', '.join(fid.lost_features) or '—'}"
        )
    lines += [
        "",
        "## Cost",
        f"- **total: ${ledger.total_usd:.3f}** for {n} story pages + cover "
        f"(≈ ${per_page:.3f}/page → ≈ ${per_page * 20:.2f} for a 20-page book; target < $3)",
        "",
        "| group | USD |",
        "|---|---|",
        *(f"| {k} | {v:.4f} |" for k, v in ledger.by_group().items()),
        "",
        "| provider/model | USD |",
        "|---|---|",
        *(f"| {k} | {v:.4f} |" for k, v in ledger.by_provider().items()),
        "",
        "## Pages",
        "| page | status | attempts | hero | companion | no text | notes |",
        "|---|---|---|---|---|---|---|",
        *pages_rows,
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "cost.json").write_text(
        json.dumps(ledger.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    provider = args.provider or settings.image_provider
    photos = [p.read_bytes() for p in args.photo]

    checks = [check_photo(b) for b in photos]
    for path, c in zip(args.photo, checks, strict=True):
        if not c.ok and not args.skip_photo_check:
            print(f"✗ {path.name}:")
            for issue in c.issues:
                print(f"   {issue.message_ar}\n   {issue.message_en}")
            return 2

    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{provider}-{args.theme}"
    out = (args.out / run_id).resolve()
    print(f"→ output: {out}")

    theme, style = load_theme(args.theme), load_style(args.style)
    child = Child(
        name=args.name,
        gender=args.gender,
        age=args.age,
        interests=[s.strip() for s in args.interests.split(",") if s.strip()],
    )

    cleaned: bytes | None = None
    companion: CompanionSpec | None = None
    if args.drawing:
        if not args.companion_name:
            print("--companion-name is required with --drawing")
            return 2
        drawing = clean_drawing(args.drawing.read_bytes())
        save(out / "companion" / "drawing-cleaned.png", drawing.png)
        cleaned = drawing.png
        save(out / "companion" / "drawing-original" / args.drawing.name, args.drawing.read_bytes())
        print(f"✓ drawing cleaned (paper found: {drawing.paper_found})")
        companion = CompanionSpec(
            name=args.companion_name,
            type_hint=args.companion_type,
            type_other=args.companion_other,
            traits=args.companion_traits,
        )

    rt = Runtime(
        settings=settings,
        text=make_text_provider(settings, "fake" if provider == "fake" else "anthropic"),
        image=make_image_provider(settings, provider),
    )
    started = time.monotonic()
    book = await generate_book(
        rt,
        BookRequest(
            child=child,
            lang=args.lang,
            theme=theme,
            style=style,
            photos=photos,
            cleaned_drawing=cleaned,
            companion=companion,
            companion_pick=args.companion_pick,
        ),
    )
    seconds = time.monotonic() - started

    # ---- raw artifacts
    save_image(out, "character-sheet", book.character_sheet)
    if book.companion_options:
        for i, opt in enumerate(book.companion_options.options, start=1):
            save_image(out / "companion", f"option-{i}", opt)
        (out / "companion" / "review.json").write_text(
            book.companion_options.review.model_dump_json(indent=2), encoding="utf-8"
        )
    (out / "story.json").write_text(book.story.model_dump_json(indent=2), encoding="utf-8")
    for p in [book.cover, *book.pages]:
        if p.image:
            save_image(out / "pages", "cover" if p.index == 0 else f"page-{p.index:02d}", p.image)
    (out / "reviews.json").write_text(
        json.dumps(
            {("cover" if p.index == 0 else p.index): p.history for p in [book.cover, *book.pages]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    missing = [p.index for p in [book.cover, *book.pages] if p.image is None]
    if missing:
        print(f"✗ pages without an image (blocked): {missing} — see reviews.json")
        write_report(out, args, book, rt, seconds, checks[0].metrics)
        return 1

    # ---- print assets (300 DPI incl. bleed)
    px = print_px(settings.print_trim_mm, settings.print_bleed_mm, settings.print_dpi)
    pdir = out / "print"
    assert book.cover.image is not None
    cover_path = save(pdir / "cover.jpg", to_print_jpeg(book.cover.image.data, px))
    texts = {p.index: p.text for p in book.story.pages}
    page_specs = []
    for p in book.pages:
        assert p.image is not None
        path = save(pdir / f"page-{p.index:02d}.jpg", to_print_jpeg(p.image.data, px))
        page_specs.append(
            PageSpec(
                index=p.index,
                image=path,
                text=texts[p.index],
                layout=theme.pages[p.index - 1].layout,
            )
        )

    keepsake = None
    if cleaned and book.companion_sheet and book.companion:
        keepsake = KeepsakeSpec(
            drawing=save(pdir / "keepsake-drawing.jpg", to_jpeg(cleaned)),
            companion=save(pdir / "keepsake-companion.jpg", to_jpeg(book.companion_sheet.data)),
            child_name=child.name,
            companion_name=book.companion.name,
            date_text=date.today().strftime("%d / %m / %Y"),
        )

    spec = BookSpec(
        lang=args.lang,
        title=book.story.title,
        dedication=book.story.dedication,
        child_name=child.name,
        cover_image=cover_path,
        pages=page_specs,
        keepsake=keepsake,
        brand=Brand(
            settings.brand_name_ar,
            settings.brand_name_en,
            settings.brand_domain,
            settings.brand_tagline_ar,
            settings.brand_tagline_en,
        ),
        watermark=args.preview,
        trim_mm=settings.print_trim_mm,
        bleed_mm=settings.print_bleed_mm,
        extra={"gender": child.gender},
    )
    rendered = await render_book(spec, out)
    write_report(out, args, book, rt, seconds, checks[0].metrics)

    print(f"✓ {rendered.interior_pdf.name}, {rendered.cover_pdf.name}")
    print(f"✓ recognizable: {book.recognizable_ratio:.0%} · total cost ${rt.ledger.total_usd:.3f}")
    print(f"  report: {out / 'report.md'}")
    return 0


def main() -> None:
    args = parse_args()
    try:
        sys.exit(asyncio.run(run(args)))
    except QamraError as e:
        print(f"✗ {type(e).__name__}: {e}\n  {e.user_message_ar}\n  {e.user_message_en}")
        sys.exit(1)


if __name__ == "__main__":
    main()
