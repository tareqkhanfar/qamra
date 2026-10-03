"""A drawn page is one continuous picture (Addendum 11): stacked bands and white margins are redrawn, while
a painted sky, a plain wall or a watercolor fade to the paper are fine."""

import io

import numpy as np
from PIL import Image

from qamra_ai.pipeline.framing import framing_problem

RNG = np.random.default_rng(7)


def png(a: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L").save(buf, "PNG")
    return buf.getvalue()


def scene() -> np.ndarray:
    """A painted picture: a soft vertical gradient with brush noise everywhere."""
    base = np.linspace(90, 200, 512)[:, None] * np.ones((1, 512))
    return base + RNG.normal(0, 8, (512, 512))


def test_a_painted_scene_is_one_picture() -> None:
    assert framing_problem(png(scene())) is None


def test_a_white_line_between_two_stacked_images_is_a_split() -> None:
    a = scene()
    a[140:146] = 254  # the p16 defect: a calm band, a white line, then the scene
    assert framing_problem(png(a)) == "split"


def test_a_flat_band_or_margin_at_an_edge_is_a_border_except_watercolor_fades() -> None:
    a = scene()
    a[:60] = 233  # the p02 defect: a pasted cream band on top
    assert framing_problem(png(a)) == "border"
    b = scene()
    b[440:] = 250 + RNG.normal(0, 2.5, (72, 512))  # a watercolor page fading to grainy paper at the bottom
    b[452:466] = 250  # with a perfectly even stretch inside it
    assert framing_problem(png(b), light_edges_ok=True) is None


def test_a_plain_painted_wall_is_not_a_band() -> None:
    a = scene()
    a[:90] = 202 + RNG.normal(0, 2.4, (90, 512))  # the watercolor p08 wall: even, but painted
    assert framing_problem(png(a)) is None
