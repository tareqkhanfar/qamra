"""The child's character: 1–3 child photos + art style → a portrait, then a sheet (front + 2 poses).

Generated once per child and reused for every book (Addendum 3 §2.2). Portrait first (owner's decision,
2026-10-10, after the likeness trial): a large head-and-shoulders portrait in the style settles the face on a
big canvas (`character_portrait.v2`), then the full-length sheet is painted from the photo and that portrait
(`character_sheet.v6`). Each step has its own model and resolution in the settings (Nano Banana Pro: the
portrait at 1K, the sheet at 2K). The parent sees the portrait first; pages and covers get it as a likeness
reference next to the sheet.

The sheet wears a neutral reference outfit; each book locks its own outfit through the cover. Hijab only when
the parent chose it. A redraw makes both again and can carry what the parent said did not look like their
child (design Create5): the chips, and the parent's own words once `character_feedback` has turned them into a
short appearance-only instruction (`note`).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from qamra_ai import prompts
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_for, negatives
from qamra_ai.pipeline.theme import ArtStyle

# What the parent can tick under "what doesn't look like her?" → the line the redraw prompt gets.
FIXES = ("skin", "face", "hair", "age")
SHEET_PROMPT_VERSION = 6  # books: portrait first. v4 (no portrait) and v5 (the trial) stay for the record
LIKENESS_SHEET_VERSION = 5  # the first version that takes a portrait
PORTRAIT_PROMPT_VERSION = 2


def fix_lines(child: Child, fixes: Sequence[str]) -> list[str]:
    lines = {
        "skin": "Skin tone: match the photo's skin tone exactly, neither lighter nor darker.",
        "face": "Face: match the photo's face shape, eyes, nose and smile more closely.",
        "hair": (
            "Hijab: keep the hijab exactly as described and the face shape from the photo."
            if child.hijab
            else "Hair: match the photo's hair color, texture, length and hairstyle exactly."
        ),
        "age": (
            f"Age: the child looked older than {child.age}; "
            "draw a younger, rounder face with child proportions."
        ),
    }
    return [lines[f] for f in FIXES if f in fixes]


def _photo_refs(photos: list[bytes]) -> list[RefImage]:
    return [RefImage(p, sniff_mime(p), f"photo of the child ({i + 1})") for i, p in enumerate(photos)]


def character_request(
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    resolution: Resolution = "1K",
    fixes: Sequence[str] = (),
    note: str | None = None,
    *,
    version: int = SHEET_PROMPT_VERSION,
    portrait: bytes | None = None,
) -> ImageRequest:
    """The character-sheet request. `portrait` (the child's portrait in the style, portrait first) goes after
    the photos as one more reference; v5 and later know it."""
    if not 1 <= len(photos) <= 3:
        raise ValueError("character sheet needs 1–3 photos")
    if portrait is not None and version < LIKENESS_SHEET_VERSION:
        raise ValueError(f"character_sheet.v{version} takes no portrait")
    h = house_for(style)
    prompt = prompts.render(
        "character_sheet",
        version=version,
        fixes=fix_lines(child, fixes),
        note=note,
        n_photos=len(photos),
        age=child.age,
        gender=child.gender,
        hijab=child.hijab,
        glasses=child.glasses,
        style=h.style,
        medium=style.guide,
        sheet=style.sheet,
        people=h.people,
        negative=negatives(h, style.negative),
        portrait=portrait is not None,
    )
    refs = _photo_refs(photos)
    if portrait is not None:
        refs.append(RefImage(portrait, sniff_mime(portrait), "the child's portrait in this book's style"))
    return ImageRequest(
        step=f"character:{attempt}",
        prompt=prompt,
        refs=refs,
        aspect="3:2",
        resolution=resolution,
        seed=attempt * 7919,
    )


def portrait_request(
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    resolution: Resolution = "1K",
    fixes: Sequence[str] = (),
    note: str | None = None,
    *,
    version: int = PORTRAIT_PROMPT_VERSION,
) -> ImageRequest:
    """Portrait first: a large head-and-shoulders portrait of the child in the style, the face filling the
    frame, from which the sheet is then painted (`character_request(..., portrait=)`)."""
    if not 1 <= len(photos) <= 3:
        raise ValueError("a portrait needs 1–3 photos")
    h = house_for(style)
    prompt = prompts.render(
        "character_portrait",
        version=version,
        fixes=fix_lines(child, fixes),
        note=note,
        n_photos=len(photos),
        age=child.age,
        gender=child.gender,
        hijab=child.hijab,
        glasses=child.glasses,
        style=h.style,
        medium=style.guide,
        negative=negatives(h, style.negative),
    )
    return ImageRequest(
        step=f"portrait:{attempt}",
        prompt=prompt,
        refs=_photo_refs(photos),
        aspect="1:1",
        resolution=resolution,
        seed=attempt * 6151,
    )


@dataclass(frozen=True)
class CharacterDrawing:
    portrait: GeneratedImage
    sheet: GeneratedImage


async def generate_character(
    rt: Runtime,
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    fixes: Sequence[str] = (),
    note: str | None = None,
) -> CharacterDrawing:
    """The portrait, then the sheet painted from the photos and it; each on its own model and resolution
    (`character_portrait_*`, `character_sheet_*` settings)."""
    s = rt.settings
    portrait = await rt.draw(
        portrait_request(child, photos, style, attempt, s.character_portrait_resolution, fixes, note),
        role="portrait",
    )
    sheet = await rt.draw(
        character_request(
            child, photos, style, attempt, s.character_sheet_resolution, fixes, note, portrait=portrait.data
        ),
        role="sheet",
    )
    return CharacterDrawing(portrait=portrait, sheet=sheet)


async def generate_character_sheet(
    rt: Runtime,
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    fixes: Sequence[str] = (),
    note: str | None = None,
) -> GeneratedImage:
    """The sheet of `generate_character` (scripts that keep only the sheet)."""
    return (await generate_character(rt, child, photos, style, attempt, fixes, note)).sheet
