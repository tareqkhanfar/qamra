import io
import itertools
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from qamra_ai.pipeline.assemble import (
    AssemblyInputs,
    assemble_book,
    dedication_text,
    portrait_from_sheet,
    split_title,
)
from qamra_ai.pipeline.book import BookInputs, run_book
from qamra_ai.pipeline.runtime import Runtime
from qamra_pdf import Brand

BRAND = Brand("قمرة", "Qamra", "qamra.app", "t", "t")


def test_split_title_ignores_tashkeel() -> None:
    assert split_title("سَلْمَى فِي أَوَّلِ يَوْمٍ", "سلمى") == ("سَلْمَى", "فِي أَوَّلِ يَوْمٍ")
    assert split_title("يوم تخرّج ليان", "ليان") == ("يوم تخرّج ليان", "")
    assert split_title("Yousef's First Day", "Yousef") == ("Yousef's First Day", "")


def test_dedication_does_not_repeat_the_opening() -> None:
    assert dedication_text("ليان", "مبارك التخرّج يا نجمتنا", "ar") == "إلى ليان… مبارك التخرّج يا نجمتنا"
    assert dedication_text("ليان", "إلى ليان… مبارك التخرّج", "ar") == "إلى ليان… مبارك التخرّج"
    assert dedication_text("ليان", "الى نجمتنا الصغيرة", "ar") == "الى نجمتنا الصغيرة"
    assert dedication_text("ليان", "حبيبتي لَيَانُ، نحبّكِ", "ar") == "حبيبتي لَيَانُ، نحبّكِ"
    assert dedication_text("Yousef", "To our brave boy", "en") == "To our brave boy"
    assert dedication_text("Yousef", "We love you!", "en") == "To Yousef… We love you!"


def test_portrait_frames_the_figure() -> None:
    sheet = Image.new("RGB", (1536, 1024), "#F6EEDC")
    draw = ImageDraw.Draw(sheet)
    draw.ellipse((180, 120, 330, 280), fill="#C98F63")  # head of the front view
    draw.rectangle((150, 280, 360, 1000), fill="#22306A")  # body
    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    portrait = Image.open(io.BytesIO(portrait_from_sheet(buf.getvalue())))
    assert portrait.size == (700, 700)
    top_center = portrait.getpixel((350, 120))
    assert isinstance(top_center, tuple) and top_center[0] > 150  # the head, not empty background


async def test_generated_book_assembles_and_passes_preflight(
    rt: Runtime, book_inputs: BookInputs, tmp_path: Path
) -> None:
    run = await run_book(rt, book_inputs, mode="final")
    assert run.story is not None
    files = await assemble_book(
        AssemblyInputs(
            run=run,
            story=run.story.out,
            child=book_inputs.child,
            lang="ar",
            brand=BRAND,
            character_sheet=book_inputs.character_sheet,
            parent_message="نحبّكِ",
            series="magic",
        ),
        tmp_path,
    )
    assert files.interior_pdf is not None and files.preflight_passed, {
        k: v.to_dict() for k, v in files.preflight.items()
    }
    kinds = [p.kind for p in files.spec.pages]
    assert len(kinds) == 24 and kinds[0] == "title" and kinds[-3:] == ["parents", "activity", "memories"]
    spread = [p for p in files.spec.pages if p.layout == "spread-panorama"]
    assert len(spread) == 6 and all(p.image is not None for p in spread)
    # Addendum 11 §3: designed layouts, never the same layout on two story beats in a row
    beats = [p.layout for p in files.spec.pages if p.kind == "story" and p.text]
    assert all(a != b for a, b in itertools.pairwise(beats)), beats
    assert len(set(beats)) >= 5
    assert not any("empty_text_box" in f for f in files.flags.values()), files.flags
    assert files.spec.spine_mm == pytest.approx(0.15 * 12 + 6.0)  # 24 pages = 12 sheets
    first_half = [p for p in spread if p.panel is not None]
    assert len(first_half) == 3 and all(p.side == "right" for p in first_half)  # RTL: text on the right page
    assert files.spec.title_page.dedication.startswith("إلى سلمى… نحبّكِ")
    assert sum(p.is_last_story for p in files.spec.pages) == 1
    # the cover names the line and the theme's ages, and gets the approved sheet for the back's figure
    assert files.spec.series == "magic" and files.spec.age_range == (
        book_inputs.theme.age_range[0],
        book_inputs.theme.age_range[1],
    )
    assert (
        files.spec.cover.hero is not None
        and files.spec.cover.hero.read_bytes() == book_inputs.character_sheet
    )


@pytest.mark.parametrize("print_files", [False])
async def test_preview_renders_only_the_proof(
    rt: Runtime, book_inputs: BookInputs, tmp_path: Path, print_files: bool
) -> None:
    run = await run_book(rt, book_inputs, mode="preview")
    assert run.story is not None
    files = await assemble_book(
        AssemblyInputs(
            run=run,
            story=run.story.out,
            child=book_inputs.child,
            lang="ar",
            brand=BRAND,
            character_sheet=book_inputs.character_sheet,
            watermark=True,
        ),
        tmp_path,
        print_files=print_files,
    )
    assert files.interior_pdf is None and files.proof_pdf is not None and not files.preflight
