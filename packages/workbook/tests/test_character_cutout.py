"""The child's figure cut from a character sheet: a cream sweater on cream paper stays whole, the floor
shadow does not come along, and the sticker edge follows the cut silhouette."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.character import PAD, cut_out, feet_cut, figure_box, is_fallback, paper_color, pose
from qamra_workbook.render.registry import Assets

from qamra_pdf.cutout import GRAIN, figure_mask, paper_grain
from qamra_pdf.cutout import cut_out as cut_out_figure_pdf

PAPER = (248, 232, 199)  # the cream paper of the sample sheets
SWEATER = (247, 228, 196)  # the lit sweater on the sample sheet: practically the paper


def _sheet(path: Path) -> None:
    w, h = 700, 600
    img = Image.new("RGB", (w, h), PAPER)
    shadow = Image.new("L", (w, h), 0)
    for cx in (175, 525):
        ImageDraw.Draw(shadow).ellipse((cx - 160, 535, cx + 150, 585), fill=220)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    img = Image.composite(Image.new("RGB", (w, h), (215, 190, 160)), img, shadow)
    d = ImageDraw.Draw(img)
    for cx in (175, 525):
        d.ellipse((cx - 60, 40, cx + 60, 170), fill=(60, 40, 30))
        d.ellipse((cx - 42, 62, cx + 42, 160), fill=(228, 180, 150))
        d.rectangle((cx - 40, 330, cx + 40, 530), fill=(45, 55, 95))
        d.ellipse((cx - 60, 515, cx, 550), fill=(120, 70, 45))
        d.ellipse((cx, 515, cx + 60, 550), fill=(120, 70, 45))
        d.rounded_rectangle(
            (cx - 70, 170, cx + 70, 330), radius=24, fill=SWEATER, outline=(233, 214, 184), width=2
        )
        d.rectangle((cx + 68, 240, cx + 71, 243), fill=SWEATER)  # a break in the faint outline
    img.filter(ImageFilter.GaussianBlur(0.7)).save(path)


def test_the_cut_figure_keeps_its_chest_and_drops_the_shadow(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    _sheet(sheet)
    for index in (0, 1):
        out = pose(sheet, tmp_path / "cut", index, max_print_mm=20, min_print_w_mm=0)  # no upscaling
        with Image.open(out) as im:
            rgba = np.asarray(im.convert("RGBA"))
        alpha = rgba[..., 3]
        h, w = alpha.shape
        # the chest (middle of the sweater) is opaque and keeps its colour (not the sticker's white)
        cy, cx = round(h * 0.45), w // 2
        chest = alpha[cy - 20 : cy + 20, cx - 30 : cx + 30]
        assert chest.min() == 255
        assert tuple(rgba[cy, cx, :3]) != (255, 255, 255)
        # the cut-out ends at the shoes (plus the thin sticker edge), not at the end of the shadow
        assert h < 600 - 40 + 30
        assert w < 230  # the figure (140 wide) and its edge, not the 310-wide shadow
    assert "-pose1" in out.name


# ---- real sheets: the clean styles cut exactly as before, the watercolour sheet cuts at all ---------------

SHEETS = Path(__file__).parent / "fixtures" / "sheets"  # the site's sample sheets (تالا, an invented child)


def _padded(img: Image.Image, paper: tuple[int, int, int]) -> Image.Image:
    padded = Image.new("RGB", (img.width + 2 * PAD, img.height + 2 * PAD), paper)
    padded.paste(img, (PAD, PAD))
    return padded


@pytest.mark.parametrize("style", ["3d", "cartoon", "semi-realistic"])
@pytest.mark.parametrize("index", [0, 1])
def test_the_clean_styles_cut_exactly_as_before(style: str, index: int) -> None:
    """The masks of the cut-out before textured paper was handled (cut-out v2, kept in `<style>-mask<i>.png`
    with the figure's box): the 3D, cartoon and semi-realistic sheets must not change."""
    with Image.open(SHEETS / f"{style}.webp") as src:
        img = src.convert("RGB")
    with Image.open(SHEETS / f"{style}-mask{index}.png") as golden_png:
        golden = np.asarray(golden_png.convert("L")) > 127
        golden_box = tuple(int(v) for v in golden_png.info["box"].split(","))
    paper = paper_color(img)
    assert paper_grain(img, paper) <= GRAIN
    box = figure_box(img, paper, index)
    assert box == golden_box
    mask = figure_mask(_padded(img.crop(box), paper), paper)
    assert mask.shape == golden.shape
    assert (mask != golden).sum() <= 0.001 * mask.size, f"{(mask != golden).sum()} pixels changed"
    assert not cut_out(img.crop(box), paper).fallback


def test_the_watercolour_sheet_is_cut_into_its_three_figures(tmp_path: Path) -> None:
    """The grainy watercolour sheet: three figures (once the whole sheet came back as one), each cut out
    cleanly (no framed portrait) with the paper around it see-through."""
    with Image.open(SHEETS / "watercolor.webp") as src:
        img = src.convert("RGB")
    paper = paper_color(img)
    assert paper_grain(img, paper) > GRAIN
    boxes = [figure_box(img, paper, i) for i in range(3)]
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        assert x1 - x0 < 0.35 * img.width and y1 - y0 > 0.75 * img.height, boxes
        assert i * img.width / 3 - 40 < (x0 + x1) / 2 < (i + 1) * img.width / 3 + 40, boxes
    sheet = tmp_path / "watercolor.png"
    img.save(sheet)
    for index in (0, 1):
        out = pose(sheet, tmp_path / "cut", index, max_print_mm=20, min_print_w_mm=0)
        assert not is_fallback(out)
        with Image.open(out) as im:
            alpha = np.asarray(im.getchannel("A"))
        h, w = alpha.shape
        assert alpha[0, 0] == alpha[0, -1] == alpha[-1, 0] == alpha[-1, -1] == 0
        assert 0.4 < (alpha > 127).mean() < 0.8  # a standing child, not the paper rectangle
        assert alpha[round(h * 0.15), w // 2] == 255 and alpha[round(h * 0.45), w // 2] == 255  # face, chest


def _busy_sheet(path: Path) -> None:
    """A full-bleed picture where a character sheet was expected: nothing can be cut out of it."""
    rng = np.random.default_rng(5)
    img = Image.new("RGB", (900, 600), (120, 160, 200))
    d = ImageDraw.Draw(img)
    for _ in range(400):
        x, y, size = int(rng.integers(-40, 900)), int(rng.integers(-40, 600)), int(rng.integers(30, 120))
        d.rectangle((x, y, x + size, y + size), fill=tuple(int(c) for c in rng.integers(30, 230, 3)))
    img.save(path)


def test_a_sheet_that_cannot_be_cut_gives_a_framed_portrait_and_says_so(tmp_path: Path) -> None:
    sheet = tmp_path / "busy.png"
    _busy_sheet(sheet)
    out = pose(sheet, tmp_path / "cut", 0, max_print_mm=20, min_print_w_mm=0)
    assert is_fallback(out)
    with Image.open(out) as im:
        alpha = np.asarray(im.getchannel("A"))
    assert alpha[0, 0] == 0 and alpha[alpha.shape[0] // 2, alpha.shape[1] // 2] == 255  # a rounded frame
    good = tmp_path / "good.png"
    _sheet(good)
    clean = pose(good, tmp_path / "cut", 0, max_print_mm=20, min_print_w_mm=0)
    assert not is_fallback(clean)
    assert Assets(LibraryStore(), out, 0.5).framed
    assert not Assets(LibraryStore(), clean, 0.5).framed
    assert Assets(LibraryStore(), clean, 0.5, family={1: (out, 0.5)}).framed  # a family member's too


def test_figures_run_together_on_textured_paper_are_split_near_the_thirds() -> None:
    """A painted floor joins the three figures of a grainy sheet into one wide run of ink: it is split at the
    emptiest columns near the thirds, never cut out as one "figure" with three children in it."""
    rng = np.random.default_rng(9)
    w, h = 1200, 800
    img = Image.new("RGB", (w, h), (250, 242, 222))
    d = ImageDraw.Draw(img)
    for cx in (200, 600, 1000):
        d.ellipse((cx - 60, 80, cx + 60, 210), fill=(70, 50, 40))
        d.rectangle((cx - 70, 210, cx + 70, 700), fill=(60, 82, 130))
    d.rectangle((40, 700, w - 40, 730), fill=(150, 120, 90))  # the floor under all three
    grain = Image.fromarray(np.clip(128 + rng.normal(0, 14, (h, w)), 0, 255).astype(np.uint8))
    grain_a = np.asarray(grain.filter(ImageFilter.GaussianBlur(0.6)), np.float32) - 128
    grainy = np.asarray(img, np.float32) + grain_a[..., None]
    img = Image.fromarray(np.clip(grainy, 0, 255).astype(np.uint8))
    paper = paper_color(img)
    assert paper_grain(img, paper) > GRAIN
    boxes = [figure_box(img, paper, i) for i in range(3)]
    for (x0, _, x1, _), cx in zip(boxes, (200, 600, 1000), strict=True):
        assert x0 <= cx - 70 and cx + 70 <= x1 and x1 - x0 < w / 2, boxes


# ---- the shoes whole («جوليا»'s white shoes, 2026-10-21) -------------------------------------------------

CREAM = (248, 237, 215)


def _sneakers_sheet(path: Path, *, soles: int = 50) -> None:
    """Three children in jeans and white sneakers on cream paper, each in a warm floor shadow, `soles` px of
    paper under the shoes (0: the drawing runs off the sheet's bottom edge)."""
    rng = np.random.default_rng(4)
    w, h = 1200, 640
    feet = h - soles
    base = np.array(CREAM, np.float32) + rng.normal(0, 0.8, (h, w, 3))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    wash = Image.new("L", (w, h), 0)
    for cx in (200, 600, 1000):
        ImageDraw.Draw(wash).ellipse((cx - 150, feet - 30, cx + 150, feet + 22), fill=230)
    img = Image.composite(
        Image.new("RGB", (w, h), (196, 168, 132)), img, wash.filter(ImageFilter.GaussianBlur(10))
    )
    d = ImageDraw.Draw(img)
    for cx in (200, 600, 1000):
        d.ellipse((cx - 60, 40, cx + 60, 170), fill=(60, 40, 30))
        d.ellipse((cx - 42, 62, cx + 42, 160), fill=(228, 180, 150))
        d.rounded_rectangle((cx - 70, 170, cx + 70, 330), radius=24, fill=(200, 70, 50))
        d.rectangle((cx - 40, 330, cx - 4, feet - 40), fill=(60, 90, 140))
        d.rectangle((cx + 4, 330, cx + 40, feet - 40), fill=(60, 90, 140))
        for x0 in (cx - 72, cx + 6):  # a white sneaker: the paper's colour in shade, strokes, straps, a sole
            y0 = feet - 46
            d.rounded_rectangle(
                (x0, y0, x0 + 66, y0 + 46), radius=16, fill=(212, 202, 186), outline=(150, 140, 128), width=2
            )
            for _ in range(40):
                x, y, tone = (
                    x0 + 6 + int(rng.integers(0, 52)),
                    y0 + 6 + int(rng.integers(0, 32)),
                    int(rng.integers(6, 34)),
                )
                d.line((x, y, x + 10, y), fill=(212 + tone, 202 + tone, 186 + tone), width=2)
            for k in range(3):
                d.line((x0 + 12, y0 + 8 + 9 * k, x0 + 52, y0 + 6 + 9 * k), fill=(165, 155, 142), width=2)
            d.line((x0 + 2, y0 + 40, x0 + 64, y0 + 40), fill=(170, 160, 148), width=2)
    img.filter(ImageFilter.GaussianBlur(0.7)).save(path)


def test_white_shoes_are_printed_whole(tmp_path: Path) -> None:
    """Both poses keep their white shoes (the floor-shadow step took them for the shadow: «جوليا»'s book
    printed her without shoes), and nothing is flagged."""
    sheet = tmp_path / "sheet.png"
    _sneakers_sheet(sheet)
    for index in (0, 1):
        out = pose(sheet, tmp_path / "cut", index, max_print_mm=20, min_print_w_mm=0)
        assert feet_cut(out) == "" and not is_fallback(out)
        with Image.open(out) as im:
            alpha = np.asarray(im.getchannel("A"))
        h, w = alpha.shape
        rows = np.flatnonzero((alpha > 127).any(1))
        # the cut-out reaches down to the soles (the figure is 590 px tall: the jeans end 90 px above it)
        assert rows[-1] > h - 12, (rows[-1], h)
        shoes = alpha[round(h * 0.9) : round(h * 0.96), round(w * 0.15) : round(w * 0.85)]
        assert (shoes > 127).mean() > 0.8
    assert not Assets(LibraryStore(), out, 0.5).feet_cut


def test_feet_cut_by_the_sheet_are_flagged(tmp_path: Path) -> None:
    """A sheet whose drawing runs off its bottom edge has the shoes cut by the drawing itself: the PNG says so
    and the book is flagged `cutout_feet` for the reviewer (a redraw of the character fixes it)."""
    sheet = tmp_path / "sheet.png"
    _sneakers_sheet(sheet, soles=0)
    out = pose(sheet, tmp_path / "cut", 0, max_print_mm=20, min_print_w_mm=0)
    assert "bottom" in feet_cut(out)
    assert Assets(LibraryStore(), out, 0.5).feet_cut
    good = tmp_path / "good.png"
    _sneakers_sheet(good)
    clean = pose(good, tmp_path / "cut", 0, max_print_mm=20, min_print_w_mm=0)
    assert Assets(LibraryStore(), clean, 0.5, family={1: (out, 0.5)}).feet_cut  # a family member's too


# ---- the segmentation model (qamra_pdf.matte): light shoes on cream paper, cut whole ---------------------

# the invented تالا's outfit-trial sheets: white sneakers in a cartoon shadow, white Mary-Janes in a
# watercolour wash. Points in the padded crop of the view (`_padded(img.crop(figure_box(...)))`), checked
# by eye.
LIGHT_SHOES = {
    ("cartoon-white-sneakers", 0): {
        "shoe": [(110, 755), (230, 750), (80, 762), (260, 765)],
        "shadow": [(45, 770), (170, 778), (300, 768)],
    },
    ("watercolor-mary-janes", 1): {
        "shoe": [(125, 706), (210, 726), (110, 700), (240, 715)],
        "shadow": [(65, 721), (300, 721), (160, 745)],
    },
}


def _view(name: str, index: int) -> tuple[Image.Image, tuple[int, int, int]]:
    with Image.open(SHEETS / f"{name}.webp") as src:
        img = src.convert("RGB")
    paper = paper_color(img)
    return _padded(img.crop(figure_box(img, paper, index)), paper), paper


@pytest.mark.matte
@pytest.mark.parametrize("case", list(LIGHT_SHOES), ids=lambda c: f"{c[0]}-{c[1]}")
def test_light_shoes_are_cut_whole_by_the_model(case: tuple[str, int]) -> None:
    """«جوليا»'s shoes (2026-10-21): white shoes on cream paper stay whole, toe to heel, and the floor shadow
    around them goes; the cut matches the reviewed one (`<name>-model<i>.png`) to 0.5 %."""
    name, index = case
    padded, paper = _view(name, index)
    cut = cut_out_figure_pdf(padded, paper)
    assert cut.method == "model" and not cut.fallback and cut.feet == ""
    mask = figure_mask(padded, paper)
    for x, y in LIGHT_SHOES[case]["shoe"]:
        assert mask[y, x], f"shoe lost at {(x, y)}"
    for x, y in LIGHT_SHOES[case]["shadow"]:
        assert not mask[y, x], f"shadow kept at {(x, y)}"
    with Image.open(SHEETS / f"{name}-model{index}.png") as golden_png:
        golden = np.asarray(golden_png.convert("L")) > 127
    assert mask.shape == golden.shape
    assert (mask != golden).sum() <= 0.005 * golden.sum(), f"{(mask != golden).sum()} pixels changed"


@pytest.mark.matte
@pytest.mark.parametrize("style", ["3d", "cartoon", "semi-realistic", "watercolor"])
def test_every_style_is_cut_by_the_model_with_its_feet(style: str) -> None:
    """The sample sheets of every style: the model's cut, no feet problem, one figure per view."""
    for index in (0, 1):
        padded, paper = _view(style, index)
        cut = cut_out_figure_pdf(padded, paper)
        assert cut.method == "model" and not cut.fallback and cut.feet == "", (style, index, cut.feet)
        mask = figure_mask(padded, paper)
        rows = np.flatnonzero(mask.any(1))
        assert rows[-1] - rows[0] > 0.8 * (mask.shape[0] - 2 * PAD)  # head to shoes


def test_two_touching_views_are_split() -> None:
    """A three-view sheet whose waving hand touches the walking pose (two runs of ink, one twice as wide):
    the wide run is split, so the waving pose's cut-out never holds two children."""
    w, h = 1200, 800
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    for cx in (200, 600, 1000):
        d.ellipse((cx - 60, 80, cx + 60, 210), fill=(70, 50, 40))
        d.rectangle((cx - 70, 210, cx + 70, 700), fill=(60, 82, 130))
    d.rectangle((670, 300, 935, 315), fill=(228, 180, 150))  # the waving arm reaching the next pose
    paper = paper_color(img)
    boxes = [figure_box(img, paper, i) for i in range(3)]
    for (x0, _, x1, _), cx in zip(boxes, (200, 600, 1000), strict=True):
        assert x0 <= cx - 70 and cx + 70 <= x1 and x1 - x0 < 420, boxes
