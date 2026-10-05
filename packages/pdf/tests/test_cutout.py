"""Figure cut-outs (qamra_pdf.cutout): a light sweater on light paper stays whole, the floor shadow goes."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from qamra_pdf.assets import cutout
from qamra_pdf.cutout import cut_out_figure, figure_mask

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
    with Image.open(dest) as out:
        assert out.mode == "RGBA"
        assert out.width < W and out.height < H  # trimmed to the figure
        alpha = np.asarray(out.getchannel("A"))
    # the sweater's middle, in the trimmed frame (top: the hair at y 40; left: the sweater at x 130)
    assert alpha[250 - 40, 200 - 130] == 255
