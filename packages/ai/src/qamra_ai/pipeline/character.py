"""Character sheet: 1–3 child photos + art style → one sheet (front + 2 poses).

Generated once per child and reused for every book (Addendum 3 §2.2). The sheet wears a neutral reference
outfit; each book locks its own outfit through the cover. Hijab only when the parent chose it. A redraw can
carry what the parent said did not look like their child (design Create5).
"""

from collections.abc import Sequence

from qamra_ai import prompts
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_for, negatives
from qamra_ai.pipeline.theme import ArtStyle

# What the parent can tick under "what doesn't look like her?" → the line the redraw prompt gets.
FIXES = ("skin", "face", "hair", "age")


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


# The sheet prompt books use: v4 (v3 + the style's own sheet line). v5 is the likeness trial's candidate
# (scripts/likeness_trial.py): the style renders and never reshapes the face; it can take a portrait too.
SHEET_PROMPT_VERSION = 4
LIKENESS_SHEET_VERSION = 5
PORTRAIT_PROMPT = ("character_portrait", 1)


def _photo_refs(photos: list[bytes]) -> list[RefImage]:
    return [RefImage(p, sniff_mime(p), f"photo of the child ({i + 1})") for i, p in enumerate(photos)]


def character_request(
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    resolution: Resolution = "1K",
    fixes: Sequence[str] = (),
    *,
    version: int = SHEET_PROMPT_VERSION,
    portrait: bytes | None = None,
) -> ImageRequest:
    """The character-sheet request. `portrait` (the child's approved portrait in the style, portrait first)
    goes after the photos as one more reference; only the v5 prompt knows it."""
    if not 1 <= len(photos) <= 3:
        raise ValueError("character sheet needs 1–3 photos")
    if portrait is not None and version < LIKENESS_SHEET_VERSION:
        raise ValueError(f"character_sheet.v{version} takes no portrait")
    h = house_for(style)
    prompt = prompts.render(
        "character_sheet",
        version=version,  # v4: v3 + the style's own sheet line, identical text for a style without one
        fixes=fix_lines(child, fixes),
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
        refs.append(
            RefImage(portrait, sniff_mime(portrait), "the child's approved portrait in this book's style")
        )
    return ImageRequest(
        step=f"character:{attempt}",
        prompt=prompt,
        refs=refs,
        aspect="3:2",
        resolution=resolution,
        seed=attempt * 7919,
    )


def portrait_request(
    child: Child, photos: list[bytes], style: ArtStyle, attempt: int = 1, resolution: Resolution = "1K"
) -> ImageRequest:
    """Portrait first (likeness trial): a large head-and-shoulders portrait of the child in the style, the
    face filling the frame, from which the sheet is then painted (`character_request(..., portrait=)`)."""
    if not 1 <= len(photos) <= 3:
        raise ValueError("a portrait needs 1–3 photos")
    h = house_for(style)
    name, version = PORTRAIT_PROMPT
    prompt = prompts.render(
        name,
        version=version,
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


async def generate_character_sheet(
    rt: Runtime,
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    fixes: Sequence[str] = (),
) -> GeneratedImage:
    return await rt.draw(character_request(child, photos, style, attempt, fixes=fixes))
