"""The segmentation model's matte (qamra_pdf.matte) and the cut-out's fallback to its colour method."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from qamra_pdf import matte
from qamra_pdf.cutout import cut_out, figure_mask


def _figure() -> Image.Image:
    img = Image.new("RGB", (300, 500), (248, 237, 215))
    d = ImageDraw.Draw(img)
    d.ellipse((100, 30, 200, 140), fill=(70, 50, 40))
    d.rounded_rectangle((90, 140, 210, 300), radius=20, fill=(200, 70, 50))
    d.rectangle((110, 300, 190, 440), fill=(60, 90, 140))
    d.ellipse((95, 430, 150, 460), fill=(90, 60, 40))
    d.ellipse((150, 430, 205, 460), fill=(90, 60, 40))
    return img


def test_without_the_model_the_colour_cut_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for value in ("off", str(tmp_path / "missing.onnx")):
        monkeypatch.setenv(matte.ENV, value)
        monkeypatch.setattr(matte, "IMAGE_PATH", tmp_path / "none.onnx")
        monkeypatch.setattr(matte, "CACHE_PATH", tmp_path / "none.onnx")
        assert matte.figure_matte(_figure()) is None
        cut = cut_out(_figure())
        assert cut.method == "colour" and not cut.fallback
        assert figure_mask(_figure())[250, 150]


def test_weights_that_are_not_the_model_are_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A file at the path that is not the checked model (a partial download, another model) is not run."""
    fake = tmp_path / "u2net.onnx"
    fake.write_bytes(b"not a model")
    monkeypatch.setenv(matte.ENV, str(fake))
    matte._session.cache_clear()
    try:
        assert not matte.available()
        assert cut_out(_figure()).method == "colour"
    finally:
        matte._session.cache_clear()


@pytest.mark.matte
def test_the_model_gives_a_matte_of_the_figure() -> None:
    a = matte.figure_matte(_figure())
    assert a is not None and a.shape == (500, 300) and a.dtype == np.float32
    assert a[250, 150] > 0.9 and a[10, 10] < 0.1  # the body, the paper
    assert cut_out(_figure()).method == "model"
