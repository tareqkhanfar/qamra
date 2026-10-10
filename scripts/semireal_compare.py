r"""«شبه حقيقي»: the v2 guide against v3, side by side, on at most two image models (Tareq, 2026-10-10).

The reference is a PHOTO, as in a customer's order: the invented girl (no real child) of the site's AI-made
lifestyle photo `apps/web/public/photos/hero-reading.jpg`, cropped here to her head and shoulders (box
`PHOTO_BOX`, no other face), then sent through exactly what an upload goes through: `qamra_api.uploads.
clean_image` (EXIF rotation, re-encoded JPEG, no metadata) and the photo check `check_photo` (one face, big
enough, sharp, well lit). The script stops if the check fails. At draw time the fal adapter downscales and
re-encodes it as it does for every order (`encode_ref`). `--ref tala` uses instead the reference of the site's
current samples: a crop of the invented تالا's watercolor sheet (itself one cause of their cartoon look).

    rows      A  v2 · Nano Banana 2              (what the site shows today)
              B  v3 · Nano Banana 2              (the prompt fix alone, same price)
              C  v2 · Nano Banana Pro
              D  v3 · Nano Banana Pro
              E  v3 · Pro sheet → Nano Banana 2 page   (the proposed mix: Pro for the once-per-child sheet)
    columns   character sheet | story page (new-sibling beat 13, the site's «smile» sample) |
              activity-book figure (the sheet's front view cut out locally, as the activity books print it)

Every prompt is the production one (`character_request`, `page_request`) with the style read from its guide:
v3 = `prompts/style/semi-realistic.md`, v2 = `prompts/style/history/semi-realistic.v2.md` (the golden prompt
snapshots prove it still sends exactly what v2 sent). The page is drawn without the companion «قمّور», so the
hero's rendering is compared on its own and no companion sheet is drawn. The activity figure costs nothing.

    uv run python scripts/semireal_compare.py                        # dry run: every call and its price
    uv run python scripts/semireal_compare.py --show-prompts         # dry run + the prompts in out/…/prompts/
    uv run python scripts/semireal_compare.py --run --max-usd 1.10   # draw on fal, never past the cap

Prices are fal's published prices for the endpoint and resolution (fal.ai model pages, checked 2026-10-10),
rounded up to the cent, never lower than `pricing.yaml`: Nano Banana 2 edit $0.08 at 1K; Nano Banana Pro edit
$0.15 at 1K and 2K (a reference image costs nothing extra). Sheets are drawn at 1K on Nano Banana 2 and at 2K
on Pro (the same price as 1K, and twice the pixels for the printed cut-out); pages at 1K. The cap covers every
run of this script: what earlier runs logged (`semireal-v3:` rows) plus this run's reservations. A call that
would pass it is skipped. Every paid call is appended to out/design-images/ledger.jsonl, a failed one too (fal
may still bill it). A cell already drawn (its file exists) is reused, so a run can be repeated after a failure
without paying twice.

The fal key comes from FAL_KEY (environment or the repo's .env); it is never printed. Output:
out/semireal-compare/<photo|tala>/ (the reference as sent, the cells, `grid.png`, `run.json`).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageDraw, ImageFont
from qamra_workbook.render.character import figure_box, front_view, is_fallback, paper_color

from qamra_ai.config import Settings
from qamra_ai.cost import fal_cost
from qamra_ai.image.base import ImageRequest, Resolution
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.image.fal import FalImageProvider
from qamra_ai.pipeline.character import character_request
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.pages import BookContext, page_request
from qamra_ai.pipeline.photo_check import PhotoCheck, check_photo
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import history_guide, house_style
from qamra_ai.pipeline.theme import ArtStyle, art_style, load_style, load_theme
from qamra_api.uploads import clean_image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "out" / "semireal-compare"
LEDGER = ROOT / "out" / "design-images" / "ledger.jsonl"
PREFIX = "semireal-v3"
RefKind = Literal["photo", "tala"]
# The site's AI-made lifestyle photo (an invented girl reading with her mother). The box is her head and
# shoulders, without the mother's face: 512 × 512, the photo check's minimum side.
PHOTO = ROOT / "apps" / "web" / "public" / "photos" / "hero-reading.jpg"
PHOTO_BOX = (1175, 560, 1687, 1072)
# تالا's published watercolor sheet: the source of the current samples' reference (scripts/style_samples.py)
TALA_SHEET = ROOT / "out" / "style-samples" / "src" / "watercolor-tala-sheet.png"
# A girl of about five in both references. No name ever reaches an image prompt.
GIRL = Child(name="تالا", gender="f", age=5)
THEME, BEAT, SEED = "new-sibling", 13, 7  # the site's «smile» sample page, and the samples' seed

NB2, PRO = "fal-ai/nano-banana-2", "fal-ai/nano-banana-pro"
SHORT = {NB2: "Nano Banana 2", PRO: "Nano Banana Pro"}
# fal's published per-image prices of the /edit endpoints (fal.ai/models/<endpoint>, checked 2026-10-10)
REAL_USD: dict[tuple[str, str], float] = {
    (f"{NB2}/edit", "0.5K"): 0.06,
    (f"{NB2}/edit", "1K"): 0.08,
    (f"{NB2}/edit", "2K"): 0.12,
    (f"{NB2}/edit", "4K"): 0.16,
    (f"{PRO}/edit", "1K"): 0.15,
    (f"{PRO}/edit", "2K"): 0.15,
    (f"{PRO}/edit", "4K"): 0.30,
}
SHEET_RES: dict[str, Resolution] = {NB2: "1K", PRO: "2K"}
PAGE_RES: Resolution = "1K"


@dataclass(frozen=True)
class Row:
    key: str
    version: Literal[2, 3]
    sheet_model: str
    page_model: str
    sheet_from: str | None = None  # another row's sheet (no sheet call)

    @property
    def label(self) -> str:
        sheet = f"sheet {SHORT[self.sheet_model]}" + (f" (row {self.sheet_from})" if self.sheet_from else "")
        return f"{self.key} · v{self.version} · {sheet} · page {SHORT[self.page_model]}"

    @property
    def sheet_key(self) -> str:
        return self.sheet_from or self.key


ROWS = (
    Row("A", 2, NB2, NB2),
    Row("B", 3, NB2, NB2),
    Row("C", 2, PRO, PRO),
    Row("D", 3, PRO, PRO),
    Row("E", 3, PRO, NB2, sheet_from="D"),
)


def folder(kind: RefKind) -> Path:
    return BASE / kind


def cell(kind: RefKind, key: str, item: Literal["sheet", "page"]) -> Path:
    return folder(kind) / f"{key}-{item}.png"


@dataclass(frozen=True)
class Call:
    kind: RefKind
    row: Row
    item: Literal["sheet", "page"]
    model: str
    endpoint: str
    resolution: str
    aspect: str
    refs: list[str]
    usd: float
    prompt: str

    @property
    def id(self) -> str:
        return f"{PREFIX}:{self.kind}:{self.row.key}:{self.item}"

    @property
    def file(self) -> Path:
        return cell(self.kind, self.row.key, self.item)


def style_of(version: int) -> ArtStyle:
    style = load_style("semi-realistic")
    if style.version == version:
        return style
    return art_style(history_guide("semi-realistic", version))


def price(endpoint: str, resolution: str) -> float:
    """fal's real price for one call, rounded up to the cent; never below pricing.yaml. Unknown: an error."""
    real = REAL_USD.get((endpoint, resolution))
    if real is None:
        raise SystemExit(f"no checked price for {endpoint} at {resolution}: check fal's page first")
    listed = fal_cost(endpoint, resolution=resolution) or 0.0
    return math.ceil(max(real, listed) * 100 - 1e-9) / 100


def photo_reference(photo: Path, box: tuple[int, int, int, int]) -> tuple[bytes, PhotoCheck]:
    """The crop as a parent would upload it, then exactly what the API stores for an order: `clean_image`,
    and the photo check that must pass (`require_face`). Stops with the check's reason otherwise."""
    with Image.open(photo) as src:
        crop = src.convert("RGB").crop(box)
    upload = io.BytesIO()
    crop.save(upload, format="PNG")  # lossless: the only JPEG step is the API's own
    stored = clean_image(upload.getvalue())
    check = check_photo(stored)
    if not check.ok:
        reasons = ", ".join(f"{i.code} ({i.message_en})" for i in check.issues)
        raise SystemExit(f"the reference photo fails the upload check: {reasons} {check.metrics}")
    return stored, check


def tala_reference(sheet: Path) -> bytes:
    """A head-and-shoulders crop of the front view of تالا's character sheet, as a PNG (the reference the
    current semi-realistic samples were drawn from)."""
    with Image.open(sheet) as src:
        img = src.convert("RGB")
    paper = paper_color(img)
    x0, y0, x1, y1 = figure_box(img, paper, 0)
    h = y1 - y0
    top, bottom = max(0, y0 - h // 20), y0 + round(h * 0.42)
    side = bottom - top
    cx = (x0 + x1) // 2
    crop = Image.new("RGB", (side, side), paper)
    crop.paste(img.crop((cx - side // 2, top, cx - side // 2 + side, bottom)), (0, 0))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return buf.getvalue()


def _rt() -> Runtime:
    settings = Settings(_env_file=None, preview_resolution=PAGE_RES)  # type: ignore[call-arg]
    return Runtime(settings=settings, text=None, image=FakeImageProvider())  # type: ignore[arg-type]


def sheet_request(row: Row, ref: bytes) -> ImageRequest:
    return character_request(GIRL, [ref], style_of(row.version), resolution=SHEET_RES[row.sheet_model])


def page_req(row: Row, sheet: bytes) -> ImageRequest:
    theme, style = load_theme(THEME), style_of(row.version)
    ctx = BookContext(
        child=GIRL,
        lang="ar",
        theme=theme,
        style=style,
        house=house_style(),  # merged with the style's own house sections by BookContext
        plan=plan_book(theme, "ar", companion_page=False),
        character_sheet=sheet,
        outfits={},
        seed=SEED,
        mode="preview",  # 1K here (`_rt`), as the samples were drawn
        companion=None,
    )
    return page_request(_rt(), ctx, BEAT, 1)


class _NoNetwork:
    async def subscribe(self, application: str, arguments: dict[str, Any], **_: Any) -> Any:
        raise RuntimeError("dry run: no network")


def provider(model: str, key: str | None) -> FalImageProvider:
    return FalImageProvider(key, model) if key else FalImageProvider(None, model, client=_NoNetwork())


def describe(kind: RefKind, row: Row, item: Literal["sheet", "page"], req: ImageRequest, model: str) -> Call:
    endpoint, args, _ = provider(model, None).build(req)
    res = str(args.get("resolution", req.resolution))
    refs = [r.label for r in req.refs]
    return Call(kind, row, item, model, endpoint, res, req.aspect, refs, price(endpoint, res), req.prompt)


def plan(rows: list[Row], ref: bytes, kind: RefKind) -> list[Call]:
    """Every paid call, in order. A page's hero reference is its row's sheet; in a dry run (no sheet yet)
    the reference stands in for it, which changes nothing in the prompt or the price."""
    calls: list[Call] = []
    for row in rows:
        if row.sheet_from is None:
            calls.append(describe(kind, row, "sheet", sheet_request(row, ref), row.sheet_model))
        sheet_file = cell(kind, row.sheet_key, "sheet")
        sheet = sheet_file.read_bytes() if sheet_file.exists() else ref
        calls.append(describe(kind, row, "page", page_req(row, sheet), row.page_model))
    return calls


def logged() -> float:
    """What earlier runs of this script logged in the shared ledger."""
    if not LEDGER.exists():
        return 0.0
    rows = (json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip())
    return float(sum(r.get("usd", 0.0) for r in rows if str(r.get("id", "")).startswith(f"{PREFIX}:")))


def ledger_row(row: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def fal_key() -> str:
    key = os.environ.get("FAL_KEY", "")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAL_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("FAL_KEY is not set (environment or .env)")
    return key


def print_plan(calls: list[Call], earlier: float, cap: float | None) -> None:
    total = 0.0
    print(f"{'call':<26} {'endpoint':<28} {'res':<4} {'aspect':<6} {'refs':<4} {'usd':>6} {'total':>6}")
    for c in calls:
        cached = c.file.exists()
        total += 0.0 if cached else c.usd
        cost = "cached" if cached else f"{c.usd:.2f}"
        where = f"{c.id:<26} {c.endpoint:<28} {c.resolution:<4} {c.aspect:<6} {len(c.refs):<4}"
        print(f"{where} {cost:>6} {total:>6.2f}")
    print(f"{len(calls)} paid calls, ${total:.2f} to spend; this script's earlier runs logged ${earlier:.2f}")
    if cap is not None:
        print(f"cap ${cap:.2f} for all runs together: ${max(0.0, cap - earlier):.2f} left before this run")
    print("+ 1 local cut-out per sheet (the activity-book figure): $0")


def write_prompts(calls: list[Call]) -> None:
    for c in calls:
        prompts = folder(c.kind) / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        refs = "\n".join(f"Image {i + 1}: {r}" for i, r in enumerate(c.refs))
        (prompts / f"{c.row.key}-{c.item}.txt").write_text(f"{refs}\n\n{c.prompt}\n", encoding="utf-8")
    if calls:
        print(f"prompts: {(folder(calls[0].kind) / 'prompts').relative_to(ROOT)}")


async def draw(rows: list[Row], ref: bytes, kind: RefKind, cap: float) -> list[dict[str, Any]]:
    key = fal_key()
    providers = {m: provider(m, key) for m in (NB2, PRO)}
    spent = logged()
    results: list[dict[str, Any]] = []
    for row in rows:  # one call at a time: the page needs its row's sheet
        for c in plan([row], ref, kind):
            if c.file.exists():
                results.append({"id": c.id, "status": "cached", "file": str(c.file.relative_to(ROOT))})
                continue
            if spent + c.usd > cap + 1e-9:
                print(f"✗ {c.id}: SKIPPED, ${spent:.2f} + ${c.usd:.2f} would pass the ${cap:.2f} cap")
                results.append({"id": c.id, "status": "skipped_cap"})
                continue
            sheet_file = cell(kind, row.sheet_key, "sheet")
            if c.item == "page" and not sheet_file.exists():
                print(f"✗ {c.id}: SKIPPED, no sheet (its sheet call failed or was skipped)")
                results.append({"id": c.id, "status": "skipped_no_sheet"})
                continue
            spent += c.usd  # reserved at the real price before the call
            req = sheet_request(row, ref) if c.item == "sheet" else page_req(row, sheet_file.read_bytes())
            t = time.time()
            base = {"id": c.id, "model": c.endpoint, "usd": c.usd, "res": c.resolution}
            try:
                image = await providers[c.model].generate(req)
            except Exception as e:  # one failure never stops the grid; it is logged at full price
                if exhausted(
                    e
                ):  # the account is empty or locked: nothing was billed, and nothing more is sent
                    ledger_row({**base, "usd": 0.0, "error": "fal_exhausted", "s": round(time.time() - t, 1)})
                    print(f"✗ {c.id}: fal says the balance is exhausted or the account locked: STOPPED")
                    results.append({"id": c.id, "status": "fal_exhausted"})
                    return await _close(providers, results, cap)
                ledger_row({**base, "error": type(e).__name__, "s": round(time.time() - t, 1)})
                print(f"✗ {c.id}: {type(e).__name__}: {str(e)[:160]}")
                results.append({"id": c.id, "status": "failed", "error": type(e).__name__})
                continue
            c.file.parent.mkdir(parents=True, exist_ok=True)
            c.file.write_bytes(image.data)
            rel = str(c.file.relative_to(ROOT))
            ledger_row({**base, "file": rel, "s": round(time.time() - t, 1)})
            print(f"✓ {c.id}: ${c.usd:.2f} ({time.time() - t:.0f}s) → {rel}")
            results.append({"id": c.id, "status": "ok", "file": rel, "usd": c.usd})
    return await _close(providers, results, cap)


def exhausted(e: Exception) -> bool:
    """fal's "Exhausted balance" / "User is locked" (a 403): the shared account is empty."""
    text = str(e).lower()
    return "exhausted" in text or "locked" in text


async def _close(
    providers: dict[str, FalImageProvider], results: list[dict[str, Any]], cap: float
) -> list[dict[str, Any]]:
    for p in providers.values():
        close = getattr(p, "aclose", None)
        if close is not None:
            await close()
    print(f"this script's spend so far (ledger): ${logged():.2f} of the ${cap:.2f} cap")
    return results


def figures(rows: list[Row], kind: RefKind) -> dict[str, Path]:
    """The activity-book figure of every drawn sheet: its front view cut out exactly as the books do."""
    out: dict[str, Path] = {}
    for row in rows:
        sheet = cell(kind, row.sheet_key, "sheet")
        if sheet.exists():
            path = front_view(sheet, folder(kind) / "figures")
            out[row.key] = path
            how = "FRAMED PORTRAIT (the cut-out failed)" if is_fallback(path) else "cut out"
            print(f"  {row.key} figure: {how}")
    return out


def grid(rows: list[Row], figs: dict[str, Path], kind: RefKind) -> Path:
    cell_h, label_w, gap = 420, 300, 12
    widths = (round(cell_h * 3 / 2), cell_h, round(cell_h * 0.62))
    width = label_w + sum(widths) + gap * 4
    canvas = Image.new("RGB", (width, gap + len(rows) * (cell_h + gap)), (246, 241, 230))
    pen = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    for i, row in enumerate(rows):
        y = gap + i * (cell_h + gap)
        label = row.label.replace(" · ", "\n") + f"\nreference: {kind}"
        pen.multiline_text((gap, y + 8), label, fill=(30, 30, 50), font=font, spacing=6)
        x = label_w + gap
        sources = (cell(kind, row.sheet_key, "sheet"), cell(kind, row.key, "page"), figs.get(row.key))
        for w, src in zip(widths, sources, strict=True):
            if src is not None and src.exists():
                with Image.open(src) as im:
                    tile = im.convert("RGBA")
                tile.thumbnail((w, cell_h), Image.Resampling.LANCZOS)
                back = Image.new("RGBA", (w, cell_h), (214, 228, 236, 255))  # the cut-out shows on a tint
                back.alpha_composite(tile, ((w - tile.width) // 2, (cell_h - tile.height) // 2))
                canvas.paste(back.convert("RGB"), (x, y))
            else:
                pen.rectangle((x, y, x + w, y + cell_h), outline=(180, 170, 150))
            x += w + gap
    path = folder(kind) / "grid.png"
    canvas.save(path)
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--run", action="store_true", help="draw on fal (without it: a dry run, no spend)")
    p.add_argument("--max-usd", type=float, help="hard cap in USD for every run of this script together")
    p.add_argument("--rows", default="A,B,C,D,E", help="which rows (default: all five)")
    p.add_argument(
        "--ref",
        choices=["photo", "tala"],
        default="photo",
        help="photo: the hero photo's invented girl, as an order sends it (default); tala: the current "
        "samples' watercolor-sheet crop",
    )
    p.add_argument("--photo", type=Path, default=PHOTO, help="the AI-made photo of an invented child")
    p.add_argument("--tala-sheet", type=Path, default=TALA_SHEET, help="تالا's published watercolor sheet")
    p.add_argument("--show-prompts", action="store_true", help="write every prompt to out/…/prompts/")
    p.add_argument(
        "--ledger",
        type=Path,
        default=LEDGER,
        help="the shared spend ledger (a worktree: the main checkout's)",
    )
    args = p.parse_args(argv)
    if args.run and args.max_usd is None:
        p.error("--run needs --max-usd")
    return args


def reference(args: argparse.Namespace) -> bytes:
    kind: RefKind = args.ref
    source: Path = args.photo if kind == "photo" else args.tala_sheet
    if not source.exists():
        raise SystemExit(f"{source} not found")
    out = folder(kind)
    out.mkdir(parents=True, exist_ok=True)
    if kind == "tala":
        ref = tala_reference(source)
        (out / "reference.png").write_bytes(ref)
        saved = (out / "reference.png").relative_to(ROOT)
        print(f"reference: تالا's watercolor sheet crop ({source.name}) → {saved}")
        return ref
    ref, check = photo_reference(source, PHOTO_BOX)
    (out / "reference.jpg").write_bytes(ref)
    m = check.metrics
    print(
        f"reference: {source.name} box {PHOTO_BOX}, as the API stores an upload "
        f"({len(ref) // 1024} KB JPEG); "
        f"photo check ok: {int(m['width'])}×{int(m['height'])}, {int(m['faces'])} face, score "
        f"{m['face_score']}, face {m['face_ratio']:.0%} of the width, sharpness {m['sharpness']}, "
        f"brightness {m['brightness']}"
    )
    return ref


def main(argv: list[str] | None = None) -> int:
    global LEDGER
    args = parse_args(argv)
    LEDGER = args.ledger
    kind: RefKind = args.ref
    keys = [k.strip().upper() for k in args.rows.split(",") if k.strip()]
    rows = [r for r in ROWS if r.key in keys]
    needed = {r.sheet_from for r in rows if r.sheet_from and r.sheet_from not in keys}
    if needed and not all(cell(kind, k, "sheet").exists() for k in needed):
        raise SystemExit(f"rows {keys} reuse the sheet of rows {sorted(needed)}: add them or draw them first")
    ref = reference(args)
    calls = plan(rows, ref, kind)
    print_plan(calls, logged(), args.max_usd)
    if args.show_prompts or args.run:
        write_prompts(calls)
    if not args.run:
        print("dry run: nothing was sent (add --run --max-usd X to draw)")
        return 0
    results = asyncio.run(draw(rows, ref, kind, args.max_usd))
    figs = figures(rows, kind)
    print(f"grid: {grid(rows, figs, kind).relative_to(ROOT)}")
    (folder(kind) / "run.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
