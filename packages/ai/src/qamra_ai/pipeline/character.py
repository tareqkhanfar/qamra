"""Character sheet: 1–3 child photos + art style → one sheet (front + 2 poses)."""

from qamra_ai import prompts
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, sniff_mime
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import ArtStyle


def character_request(child: Child, photos: list[bytes], style: ArtStyle, attempt: int = 1) -> ImageRequest:
    if not 1 <= len(photos) <= 3:
        raise ValueError("character sheet needs 1–3 photos")
    prompt = prompts.render(
        "character_sheet",
        n_photos=len(photos),
        age=child.age,
        gender=child.gender,
        style_guide=style.guide,
    )
    refs = [RefImage(p, sniff_mime(p), f"photo of the child ({i + 1})") for i, p in enumerate(photos)]
    return ImageRequest(step=f"character:{attempt}", prompt=prompt, refs=refs, aspect="3:2")


async def generate_character_sheet(
    rt: Runtime, child: Child, photos: list[bytes], style: ArtStyle, attempt: int = 1
) -> GeneratedImage:
    return await rt.draw(character_request(child, photos, style, attempt))
