"""Character sheet: 1–3 child photos + art style → one sheet (front + 2 poses).

Generated once per child and reused for every book (Addendum 3 §2.2). The sheet wears a neutral reference
outfit; each book locks its own outfit through the cover. Hijab only when the parent chose it.
"""

from qamra_ai import prompts
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import ArtStyle


def character_request(
    child: Child, photos: list[bytes], style: ArtStyle, attempt: int = 1, resolution: Resolution = "1K"
) -> ImageRequest:
    if not 1 <= len(photos) <= 3:
        raise ValueError("character sheet needs 1–3 photos")
    h = house_style()
    prompt = prompts.render(
        "character_sheet",
        version=2,
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
    rt: Runtime, child: Child, photos: list[bytes], style: ArtStyle, attempt: int = 1
) -> GeneratedImage:
    return await rt.draw(character_request(child, photos, style, attempt))
