from pathlib import Path

import pytest
from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.image.fallback import FallbackImageProvider
from qamra_ai.pipeline.book import BookInputs, default_companion
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import Theme, load_style, load_theme

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
def fake_image() -> FakeImageProvider:
    return FakeImageProvider(long_side=128)


@pytest.fixture
def rt(settings: Settings, fake_image: FakeImageProvider) -> Runtime:
    return Runtime(
        settings=settings,
        text=default_fake_text_provider(),
        image=FallbackImageProvider(fake_image, base_delay=0),
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
def theme() -> Theme:
    return load_theme("first-day")


@pytest.fixture
def style():  # type: ignore[no-untyped-def]
    return load_style("watercolor")


@pytest.fixture
def book_inputs(child: Child, theme: Theme, style) -> BookInputs:  # type: ignore[no-untyped-def]
    return BookInputs(
        child=child,
        lang="ar",
        theme=theme,
        style=style,
        character_sheet=png("tan", (96, 64)),
        companion=default_companion(theme, "ar"),
        seed=1234,
    )
