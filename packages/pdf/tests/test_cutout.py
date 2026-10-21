"""Figure cut-outs (qamra_pdf.cutout): a light sweater on light paper stays whole, the floor shadow goes."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from qamra_pdf.assets import cutout
from qamra_pdf.cutout import (
    GRAIN,
    _figure,
    _measure,
    cut_out,
    cut_out_figure,
    feet_problem,
    figure_mask,
    mask_problem,
    paper_grain,
)

PAPER = (250, 247, 240)
SWEATER = (251, 248, 241)  # the lit sweater: the paper's own colour, as the image model draws it
W, H = 400, 600

# where things are on the synthetic sheet
SWEATER_BOX = (130, 170, 270, 330)
SHADOW_SPOTS = [(40, 560), (90, 565), (320, 565), (360, 560)]  # floor shadow, clear of the shoes


def _figure_on_paper(*, outline_gap: bool = True) -> Image.Image:
    """A child: dark hair, skin face, a near-white sweater with only a faint soft outline (broken in one
    place, as on the lit side of a real drawing), navy trousers, brown shoes, a soft grey floor shadow."""
    rng = np.random.default_rng(7)
    base = np.array(PAPER, np.float32) + rng.normal(0, 0.8, (H, W, 3))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).ellipse((20, 535, 380, 590), fill=220)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    img = Image.composite(Image.new("RGB", (W, H), (205, 196, 180)), img, shadow)

    d = ImageDraw.Draw(img)
    d.ellipse((140, 40, 260, 170), fill=(60, 40, 30))  # hair
    d.ellipse((158, 62, 242, 160), fill=(228, 180, 150))  # face
    d.rectangle((160, 330, 240, 530), fill=(45, 55, 95))  # trousers
    d.rectangle((198, 400, 202, 530), fill=PAPER)  # the paper between the legs (open at the bottom)
    d.ellipse((140, 515, 200, 550), fill=(120, 70, 45))  # shoes
    d.ellipse((200, 515, 260, 550), fill=(120, 70, 45))
    d.rounded_rectangle(SWEATER_BOX, radius=24, fill=SWEATER, outline=(232, 226, 214), width=2)
    if outline_gap:
        d.rectangle((268, 240, 271, 243), fill=SWEATER)  # a 4-px break in the outline, on the lit side
    # shading on the sweater's shadow side, like a soft 3-D render
    d.rectangle((136, 200, 150, 320), fill=(238, 233, 222))
    return img.filter(ImageFilter.GaussianBlur(0.7))


def test_a_near_white_sweater_on_white_paper_stays_fully_opaque() -> None:
    img = _figure_on_paper()
    alpha = np.asarray(cut_out_figure(img).getchannel("A"))
    x0, y0, x1, y1 = SWEATER_BOX
    for inner in (alpha[y0 + 6 : y1 - 6, x0 + 26 : x1 - 26], alpha[y0 + 26 : y1 - 26, x0 + 6 : x1 - 6]):
        assert inner.min() == 255, f"{(inner < 255).sum()} sweater pixels are see-through"


def test_the_floor_shadow_and_the_paper_are_removed() -> None:
    img = _figure_on_paper()
    alpha = np.asarray(cut_out_figure(img).getchannel("A"))
    for x, y in SHADOW_SPOTS:
        assert alpha[y, x] == 0, f"shadow kept at {(x, y)}"
    assert alpha[10, 10] == 0 and alpha[300, 40] == 0 and alpha[300, 360] == 0
    # nothing pale is left under the feet: below the shoes everything is transparent
    assert alpha[560:, :].max() == 0


def test_the_figure_itself_is_whole() -> None:
    mask = figure_mask(_figure_on_paper())
    assert mask[100, 200]  # face
    assert mask[80, 160]  # hair
    assert mask[450, 180] and mask[450, 220]  # trousers
    assert mask[530, 170] and mask[530, 230]  # shoes
    assert mask[250, 200]  # the middle of the chest


def test_without_the_gap_the_result_is_the_same() -> None:
    a = figure_mask(_figure_on_paper(outline_gap=True))
    b = figure_mask(_figure_on_paper(outline_gap=False))
    assert (a != b).sum() < 40  # only the few pixels of the gap itself may differ


def test_assets_cutout_keeps_the_sweater_and_trims(tmp_path: Path) -> None:
    src = tmp_path / "companion.jpg"
    _figure_on_paper().save(src, quality=92)
    dest = cutout(src, tmp_path / "companion.png")
    assert dest is not None
    with Image.open(dest) as out:
        assert out.mode == "RGBA"
        assert out.width < W and out.height < H  # trimmed to the figure
        alpha = np.asarray(out.getchannel("A"))
    # the sweater's middle, in the trimmed frame (top: the hair at y 40; left: the sweater at x 130)
    assert alpha[250 - 40, 200 - 130] == 255


# ---- textured (watercolour) paper and the safety check ---------------------------------------------------

WC_PAPER = (250, 242, 222)
WC_SWEATER = (246, 237, 216)  # a cream sweater: a few steps off the paper, well inside the paper's grain


def _grain(rng: np.random.Generator, w: int, h: int) -> np.ndarray:
    """Watercolour paper: a fine 1–2 px grain (±10 or so) on a soft, blotchy tint (±5)."""
    fine = Image.fromarray(np.clip(128 + rng.normal(0, 14, (h, w)), 0, 255).astype(np.uint8))
    fine_a = np.asarray(fine.filter(ImageFilter.GaussianBlur(0.6)), np.float32) - 128
    blotch = Image.fromarray(np.clip(128 + rng.normal(0, 40, (9, 6)), 0, 255).astype(np.uint8))
    blotch_a = np.asarray(blotch.resize((w, h), Image.Resampling.BICUBIC), np.float32) - 128
    grain: np.ndarray = fine_a + blotch_a / 8
    return grain


def _watercolour_sheet() -> tuple[Image.Image, np.ndarray]:
    """A child painted in soft washes on grainy, tinted paper (as the watercolour sheets are): no hard
    outlines except a faint one round a cream sweater, soft edges everywhere, a soft floor shadow; and the
    true figure."""
    rng = np.random.default_rng(11)
    img = Image.new("RGB", (W, H), WC_PAPER)
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).ellipse((40, 540, 360, 585), fill=170)
    img = Image.composite(
        Image.new("RGB", (W, H), (214, 200, 172)), img, shadow.filter(ImageFilter.GaussianBlur(9))
    )

    truth = Image.new("L", (W, H), 0)
    t = ImageDraw.Draw(truth)

    def wash(shape: str, box: tuple[int, int, int, int], colour: tuple[int, int, int], soft: float) -> None:
        nonlocal img
        layer = Image.new("L", (W, H), 0)
        getattr(ImageDraw.Draw(layer), shape)(box, fill=255)
        getattr(t, shape)(box, fill=255)
        img = Image.composite(
            Image.new("RGB", (W, H), colour), img, layer.filter(ImageFilter.GaussianBlur(soft))
        )

    wash("ellipse", (140, 40, 260, 170), (88, 62, 48), 2.0)  # hair
    wash("ellipse", (158, 66, 242, 160), (226, 176, 146), 1.5)  # face
    wash("rectangle", (160, 330, 240, 530), (60, 82, 130), 2.5)  # trousers, no outline
    wash("ellipse", (140, 515, 200, 550), (92, 96, 120), 1.5)  # shoes
    wash("ellipse", (200, 515, 260, 550), (92, 96, 120), 1.5)
    sweater = Image.new("RGB", (W, H), WC_SWEATER)
    d = ImageDraw.Draw(sweater)
    d.rounded_rectangle(SWEATER_BOX, radius=24, outline=(196, 160, 128), width=2)  # a faint brown line
    layer = Image.new("L", (W, H), 0)
    ImageDraw.Draw(layer).rounded_rectangle(SWEATER_BOX, radius=24, fill=255)
    t.rounded_rectangle(SWEATER_BOX, radius=24, fill=255)
    img = Image.composite(
        sweater.filter(ImageFilter.GaussianBlur(0.8)), img, layer.filter(ImageFilter.GaussianBlur(0.8))
    )

    painted = np.asarray(img, np.float32) + _grain(rng, W, H)[..., None]  # the pigment shows the grain too
    return Image.fromarray(np.clip(painted, 0, 255).astype(np.uint8)), np.asarray(truth) > 127


def test_a_soft_figure_on_grainy_watercolour_paper_is_cut_cleanly() -> None:
    img, truth = _watercolour_sheet()
    assert paper_grain(img) > GRAIN  # the textured branch is the one under test
    cut = cut_out(img)
    assert not cut.fallback, cut.reason
    mask = figure_mask(img)
    assert mask_problem(mask) == ""
    # the figure is whole: its body (6 px in from the soft edges) is all kept, the cream chest included
    inner = np.asarray(Image.fromarray(truth).filter(ImageFilter.MinFilter(13)))
    assert not (inner & ~mask).any(), f"{(inner & ~mask).sum()} figure pixels lost"
    # and nothing of the paper comes along: hardly a pixel more than 6 px out from the figure
    outer = np.asarray(Image.fromarray(truth).filter(ImageFilter.MaxFilter(13)))
    assert (mask & ~outer).sum() < 0.003 * mask.size, f"{(mask & ~outer).sum()} paper pixels kept"
    for x, y in [*SHADOW_SPOTS, (10, 10), (40, 300), (360, 300), (200, 590)]:
        assert not mask[y, x], f"paper or shadow kept at {(x, y)}"


def _busy_picture() -> Image.Image:
    """A picture with no paper to find (a full-bleed scene passed where a character sheet was expected)."""
    rng = np.random.default_rng(3)
    img = Image.new("RGB", (W, H), (120, 160, 200))
    d = ImageDraw.Draw(img)
    for _ in range(160):
        x, y = int(rng.integers(-40, W)), int(rng.integers(-40, H))
        size = int(rng.integers(30, 120))
        colour = tuple(int(c) for c in rng.integers(30, 230, 3))
        d.rectangle((x, y, x + size, y + size), fill=colour)  # type: ignore[arg-type]
    return img


def test_a_picture_that_cannot_be_cut_out_becomes_a_framed_portrait() -> None:
    img = _busy_picture()
    cut = cut_out(img)
    assert cut.fallback and cut.reason
    assert cut.image.mode == "RGBA" and cut.image.size == img.size
    alpha = np.asarray(cut.image.getchannel("A"))
    assert alpha[H // 2, W // 2] == 255  # the picture inside the frame
    assert alpha[0, 0] == alpha[0, -1] == alpha[-1, 0] == alpha[-1, -1] == 0  # its corners are round
    assert (alpha == 255).mean() > 0.9  # not a cut-out of a few pieces: a whole portrait
    assert np.asarray(cut_out_figure(img).getchannel("A")).tobytes() == alpha.tobytes()


def test_a_companion_that_cannot_be_cut_out_is_left_out(tmp_path: Path) -> None:
    """The story's back cover puts the companion beside the hero only when it cuts out: never a framed card
    (or, as before the safety check, the whole many-view sheet with ragged paper)."""
    src = tmp_path / "companion.png"
    _busy_picture().save(src)
    assert cutout(src, tmp_path / "companion-cut.png") is None
    assert not (tmp_path / "companion-cut.png").exists()


def test_the_safety_check() -> None:
    blank = np.zeros((100, 80), bool)
    figure = blank.copy()
    figure[20:80, 20:60] = True
    assert mask_problem(figure) == ""
    assert "covers" in mask_problem(~blank)
    assert "only" in mask_problem(blank)
    touching = figure.copy()
    touching[0, 40] = touching[-1, 40] = touching[50, 0] = touching[50, -1] = True
    assert "four edges" in mask_problem(touching)


def test_a_clean_sheet_is_not_taken_for_textured_paper() -> None:
    assert paper_grain(_figure_on_paper()) <= GRAIN


# ---- white shoes and the feet check («جوليا»'s shoes, 2026-10-21) ------------------------------------------

CREAM = (248, 237, 215)  # the cream paper of «جوليا»'s sheet
SOLES = 46  # px of paper under the soles on the synthetic figure


def _shoe(d: ImageDraw.ImageDraw, x0: int, y0: int, rng: np.random.Generator) -> None:
    """A white sneaker as the image model paints it on cream paper: the paper's colour in shade, with brush
    strokes, straps and a sole line (`_white_shoes`)."""
    d.rounded_rectangle(
        (x0, y0, x0 + 66, y0 + 46), radius=16, fill=(212, 202, 186), outline=(150, 140, 128), width=2
    )
    for _ in range(40):
        x, y, tone = (
            x0 + 6 + int(rng.integers(0, 52)),
            y0 + 6 + int(rng.integers(0, 32)),
            int(rng.integers(6, 34)),
        )
        d.line(
            (x, y, x + int(rng.integers(6, 14)), y + int(rng.integers(-2, 3))),
            fill=(212 + tone, 202 + tone, 186 + tone),
            width=2,
        )
    for k in range(3):
        d.line((x0 + 12, y0 + 8 + 9 * k, x0 + 52, y0 + 6 + 9 * k), fill=(165, 155, 142), width=2)
    d.line((x0 + 2, y0 + 40, x0 + 64, y0 + 40), fill=(170, 160, 148), width=2)


def _white_shoes(*, shadow: bool = True, soles: int = SOLES) -> Image.Image:
    """A child in jeans and white sneakers on cream paper, in a warm floor shadow (a wash that makes the paper
    darker and redder) or none; `soles` px of paper under the shoes (0: the drawing runs off the bottom)."""
    rng = np.random.default_rng(3)
    base = np.array(CREAM, np.float32) + rng.normal(0, 0.8, (H, W, 3))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    feet = H - soles
    if shadow:
        wash = Image.new("L", (W, H), 0)
        ImageDraw.Draw(wash).ellipse((40, feet - 30, 360, feet + 22), fill=230)
        img = Image.composite(
            Image.new("RGB", (W, H), (196, 168, 132)), img, wash.filter(ImageFilter.GaussianBlur(10))
        )
    d = ImageDraw.Draw(img)
    d.ellipse((140, 40, 260, 170), fill=(60, 40, 30))  # hair
    d.ellipse((158, 62, 242, 160), fill=(228, 180, 150))  # face
    d.rounded_rectangle((130, 170, 270, 330), radius=24, fill=(200, 70, 50))  # a red top
    d.rectangle((160, 330, 196, feet - 40), fill=(60, 90, 140))  # jeans
    d.rectangle((204, 330, 240, feet - 40), fill=(60, 90, 140))
    _shoe(d, 128, feet - 46, rng)
    _shoe(d, 206, feet - 46, rng)
    return img.filter(ImageFilter.GaussianBlur(0.7))


def _shoes(mask: np.ndarray, soles: int = SOLES) -> float:
    """The share of the two shoes (inside their outlines) that the cut keeps."""
    y0, y1 = H - soles - 40, H - soles - 6
    return float(np.concatenate([mask[y0:y1, 136:186].ravel(), mask[y0:y1, 214:264].ravel()]).mean())


def test_white_shoes_in_a_warm_floor_shadow_stay_and_the_shadow_goes() -> None:
    """The bug: by hue a white shoe on cream paper is "paper in shade", so the floor-shadow step took both
    shoes away (cut-out v3 kept 6 % of them). The shadow's warm tint tells them apart now."""
    img = _white_shoes()
    cut = cut_out(img)
    assert not cut.fallback and cut.feet == ""
    mask = figure_mask(img)
    assert _shoes(mask) > 0.97, f"only {_shoes(mask):.0%} of the shoes kept"
    for x in (55, 90, 300, 345):  # the shadow beside the shoes goes
        assert not mask[H - SOLES - 10, x], f"shadow kept at x={x}"
    assert not mask[H - SOLES + 12 :, :].any()  # nothing pale is left under the shoes


def test_white_shoes_without_a_shadow_stay() -> None:
    mask = figure_mask(_white_shoes(shadow=False))
    assert _shoes(mask) > 0.97
    assert cut_out(_white_shoes(shadow=False)).feet == ""


def test_dark_shoes_cut_as_before() -> None:
    """Dark shoes (and the light sweater) cut as before: see also the workbook's golden masks."""
    mask = figure_mask(_figure_on_paper())
    assert mask[530, 170] and mask[530, 230]
    assert cut_out(_figure_on_paper()).feet == ""


def test_a_figure_that_runs_off_the_bottom_is_reported() -> None:
    """Shoes cut by the drawing itself (no paper under them) cannot be mended by the cut-out: it says so, and
    the books flag it for the reviewer (a redraw fixes it)."""
    cut = cut_out(_white_shoes(soles=0))
    assert not cut.fallback
    assert "bottom" in cut.feet


def test_lost_shoes_are_reported() -> None:
    """The feet check sees drawing with hard edges left under the legs: what the floor-shadow step did to
    «جوليا»'s white shoes before (simulated: the shoes taken out of a good mask)."""
    img = _white_shoes()
    p = _measure(img)
    mask = _figure(p)
    assert feet_problem(p, mask) == ""
    without = mask.copy()
    without[H - SOLES - 47 :, :] = False  # the cut ends at the hem of the jeans
    assert "under the feet" in feet_problem(p, without)
