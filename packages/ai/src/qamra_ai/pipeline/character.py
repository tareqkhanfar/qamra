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
from qamra_ai.pipeline.style import house_style
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


def character_request(
    child: Child,
    photos: list[bytes],
    style: ArtStyle,
    attempt: int = 1,
    resolution: Resolution = "1K",
    fixes: Sequence[str] = (),
) -> ImageRequest:
    if not 1 <= len(photos) <= 3:
        raise ValueError("character sheet needs 1–3 photos")
    h = house_style()
    prompt = prompts.render(
        "character_sheet",
        version=3,
        fixes=fix_lines(child, fixes),
        n_photos=len(photos),
        age=child.age,
        gender=child.gender,
        hijab=child.hijab,
        glasses=child.glasses,
        style=h.style,
        medium=style.guide,
        people=h.people,
        negative=h.negative,
    )
    refs = [RefImage(p, sniff_mime(p), f"photo of the child ({i + 1})") for i, p in enumerate(photos)]
    return ImageRequest(
        step=f"character:{attempt}",
        prompt=prompt,
        refs=refs,
        aspect="3:2",
        resolution=resolution,
        seed=attempt * 7919,
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
