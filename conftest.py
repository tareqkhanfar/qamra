import pytest

pytest_plugins = ["qamra_core.testing"]


@pytest.fixture(autouse=True)
def _colour_cutouts_unless_asked(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests cut figures with the colour method (their synthetic figures are shapes, not drawings, and the
    model's weights are not in every checkout); a test marked `matte` uses the segmentation model
    (`qamra_pdf.matte`) and is skipped where its weights are missing."""
    if request.node.get_closest_marker("matte") is None:
        monkeypatch.setenv("QAMRA_MATTE_MODEL", "off")
        return
    from qamra_pdf import matte

    if not matte.available():
        pytest.skip("the segmentation model is not installed (scripts/fetch_matte_model.py)")
