"""The child's figure cut from a character sheet: a cream sweater on cream paper stays whole, the floor
shadow does not come along, and the sticker edge follows the cut silhouette."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from qamra_workbook.render.character import pose

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
        out = pose(sheet, tmp_path / "cut", index, max_print_mm=20)  # small: no upscaling in the test
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
