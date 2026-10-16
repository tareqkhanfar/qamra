"""The Classic hero blend (2026-10-16 fix of the violet patches): only the head and hair come from the edit,
through a soft mask, colour-matched and aligned; every other pixel stays the template's."""

import io

import cv2
import numpy as np
from PIL import Image, ImageDraw

from qamra_ai.pipeline.classic_blend import align, blend_head, head_mask, match_colors, ring_around
from qamra_ai.pipeline.classic_geometry import HeroBox, head_crop_rect, head_of

BG = (236, 222, 196)  # warm paper
GOWN = (122, 150, 120)  # sage green
SKIN = (226, 176, 140)
HAIR = (30, 30, 34)


def _page(size: tuple[int, int] = (1200, 1200), ponytail: bool = True) -> Image.Image:
    """A template page: paper, a green gown, a head with black hair (and a ponytail), a cream companion."""
    page = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(page)
    d.rectangle((420, 640, 780, 1200), fill=GOWN)
    d.ellipse((460, 360, 740, 640), fill=SKIN)
    d.pieslice((450, 340, 750, 620), 180, 360, fill=HAIR)
    if ponytail:
        d.ellipse((380, 450, 470, 720), fill=HAIR)  # down the side of the shoulder
    d.ellipse((180, 520, 300, 640), fill=(245, 235, 200))  # the companion, beside the hero
    for x in range(0, size[0], 40):  # paper texture lines, so alignment has something to hold
        d.line((x, 0, x, size[1]), fill=(226, 212, 186), width=2)
    return page


HEAD = HeroBox(380 / 1200, 340 / 1200, 370 / 1200, 300 / 1200)  # hair, ponytail top and face
FIGURE = HeroBox(0.3, 0.28, 0.4, 0.72, HEAD)


def _rects(page: Image.Image) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    rect = head_crop_rect(head_of(FIGURE), page.width, page.height)
    return rect, head_of(FIGURE).rect(page.width, page.height)


def _edited(page: Image.Image, rect: tuple[int, int, int, int], *, tint: tuple[int, int, int]) -> Image.Image:
    """What klein returns: the crop with a new child (brown hair, no ponytail) and a violet wash on top."""
    crop = page.crop(rect)
    d = ImageDraw.Draw(crop)
    ox, oy = rect[0], rect[1]
    d.ellipse((380 - ox, 450 - oy, 470 - ox, 720 - oy), fill=BG)  # the ponytail is gone
    d.pieslice((450 - ox, 340 - oy, 750 - ox, 620 - oy), 180, 360, fill=(150, 100, 60))  # brown hair
    arr = np.asarray(crop).astype(np.int16) + np.array(tint, np.int16)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def test_only_the_head_changes_and_the_rest_is_the_template_exactly() -> None:
    page = _page()
    rect, head = _rects(page)
    out, alpha = blend_head(page, _edited(page, rect, tint=(18, -6, 30)), rect, head)
    a = np.asarray(alpha)
    before, after = np.asarray(page), np.asarray(out)
    outside = np.ones(before.shape[:2], bool)
    outside[rect[1] : rect[3], rect[0] : rect[2]] = a == 0
    assert np.array_equal(before[outside], after[outside])  # every pixel outside the soft mask: unchanged
    left, top = rect[0], rect[1]
    assert a[0, :].max() == a[-1, :].max() == a[:, 0].max() == a[:, -1].max() == 0  # no edge at the crop
    assert np.isin(np.unique(a), [0, 255]).mean() < 0.5  # feathered: many in-between values
    cx, cy = (head[0] + head[2]) // 2 - left, (head[1] + head[3]) // 2 - top
    assert a[cy - 80, cx] == 255  # the hair: all from the edit
    hair = after[head[1] + 30, (head[0] + head[2]) // 2]
    # brown: the violet wash (+30 blue) is taken off
    assert abs(int(hair[0]) - 150) < 20 and abs(int(hair[2]) - 60) < 20
    assert tuple(after[1100, 610]) == GOWN  # the clothes stay the template's
    assert tuple(after[580, 240]) == tuple(before[580, 240])  # the companion beside the hero too
    assert (a > 0).sum() < 0.6 * a.size  # the head, not the crop's rectangle


def test_the_old_ponytail_goes_with_the_old_hair() -> None:
    page = _page()
    rect, head = _rects(page)
    out, _ = blend_head(page, _edited(page, rect, tint=(0, 0, 0)), rect, head)
    tail = np.asarray(out)[690, 425]  # the ponytail's lower end, below the head box
    assert int(tail.mean()) > 150  # paper now, not black: no half-blended ghost of the old hair


def test_head_mask_is_rounded_and_inside_the_crop() -> None:
    mask = head_mask((400, 400), (100, 100, 300, 300))
    assert mask[200, 200] == 255 and mask[5, 5] == 0
    assert mask[100 - 10, 100 - 10] == 0  # the corner is rounded, not a rectangle
    ring = ring_around(mask, 200)
    assert ring[200, 200] == 0 and ring.max() == 255


def test_colour_matching_takes_a_wash_off() -> None:
    page = np.asarray(_page())[300:800, 300:800].copy()
    washed = np.clip(page.astype(np.int16) + np.array([20, -10, 35]), 0, 255).astype(np.uint8)
    ring = np.zeros(page.shape[:2], np.uint8)
    ring[:60, :] = 255
    fixed = match_colors(washed, page, ring)
    assert np.abs(fixed[:60].astype(int) - page[:60].astype(int)).mean() < 4


def test_alignment_undoes_a_zoomed_edit() -> None:
    page = np.asarray(_page())[200:1000, 200:1000].copy()
    zoom = cv2.warpAffine(page, cv2.getRotationMatrix2D((400, 400), 0, 1.12), (800, 800))
    keep = np.full(page.shape[:2], 255, np.uint8)
    moved, valid = align(zoom, page, keep)
    inner = valid > 0
    err = np.abs(moved.astype(int) - page.astype(int))[inner].mean()
    assert err < np.abs(zoom.astype(int) - page.astype(int)).mean() / 3


def test_head_boxes_round_trip_mirror_and_fallback() -> None:
    box = FIGURE
    data = box.to_dict()
    assert data["head"]["w"] == round(HEAD.w, 4)
    again = HeroBox.from_dict(data)
    assert again is not None and again.head is not None and abs(again.head.x - HEAD.x) < 1e-3
    mirrored = box.mirrored()
    assert mirrored.head is not None and abs(mirrored.head.x - (1 - HEAD.x - HEAD.w)) < 1e-6
    assert HeroBox(0.1, 0.1, 0.2, 0.2).with_head(HeroBox(0.6, 0.6, 0.1, 0.1)).head is None  # not inside
    plain = HeroBox(0.2, 0.2, 0.4, 0.6)
    assert head_of(plain) == HeroBox(0.2 + 0.4 * 0.08, 0.2, 0.4 * 0.84, 0.6 * 0.42)  # the top of the figure


def test_blend_handles_a_crop_on_the_page_border() -> None:
    page = _page((900, 900))
    rect = (0, 300, 600, 900)  # touches the left and bottom page edges
    head = (100, 380, 400, 640)
    edit = Image.new("RGB", (rect[2] - rect[0], rect[3] - rect[1]), (90, 60, 40))
    out, alpha = blend_head(page, edit, rect, head)
    assert out.size == page.size and np.asarray(alpha).max() == 255
    buf = io.BytesIO()
    out.save(buf, format="JPEG")  # a printable page
