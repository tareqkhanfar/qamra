from pathlib import Path

import pytest

from qamra_ai.config import Settings
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_style, load_theme

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        image_provider="fake",
        text_provider="fake",  # type: ignore[call-arg]
        image_concurrency=3,
    )


@pytest.fixture
def rt(settings: Settings) -> Runtime:
    return Runtime(
        settings=settings, text=default_fake_text_provider(), image=FakeImageProvider(long_side=256)
    )


@pytest.fixture
def face_png() -> bytes:
    return (FIXTURES / "face-astronaut-public-domain.png").read_bytes()


@pytest.fixture
def drawing_paths() -> list[Path]:
    return sorted((FIXTURES / "drawings").glob("drawing-*.jpg"))


@pytest.fixture
def child() -> Child:
    return Child(name="سلمى", gender="f", age=5, interests=["الرسم"])


@pytest.fixture
def theme():  # type: ignore[no-untyped-def]
    return load_theme("first-day")


@pytest.fixture
def style():  # type: ignore[no-untyped-def]
    return load_style("watercolor")
