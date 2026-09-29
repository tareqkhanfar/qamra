"""Companion from a child's drawing (Addendum 1 §1): review+describe → 2 faithful sheet options."""

import asyncio
from dataclasses import dataclass

from qamra_ai import prompts
from qamra_ai.errors import ContentBlocked
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, sniff_mime
from qamra_ai.pipeline.models import CompanionFidelity, CompanionSpec, DrawingReview
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import ArtStyle
from qamra_ai.text.base import ImagePart

TYPE_LABELS = {"creature": "friendly creature", "animal": "animal", "robot": "robot"}

DRAWING_REJECTED_AR = "هذه الرسمة لا تناسب كتاب أطفال. جرّبوا رسمة أخرى لصاحبٍ لطيف."
DRAWING_REJECTED_EN = "This drawing doesn't fit a children's book. Please try another friendly companion."


def type_label(spec: CompanionSpec) -> str:
    if spec.type_hint == "other":
        return spec.type_other or "friendly creature"
    return TYPE_LABELS[spec.type_hint]


class DrawingRejected(ContentBlocked):
    user_message_ar = DRAWING_REJECTED_AR
    user_message_en = DRAWING_REJECTED_EN


async def review_drawing(rt: Runtime, cleaned_png: bytes, spec: CompanionSpec) -> DrawingReview:
    system = prompts.render(
        "companion_describe", type_label=type_label(spec), name=spec.name, traits=spec.traits
    )
    review = await rt.ask(
        step="companion:review",
        system=system,
        user=[ImagePart(cleaned_png, "image/png"), "Review this drawing."],
        schema=DrawingReview,
        fast=True,
    )
    if not review.safe or not review.is_drawing:
        raise DrawingRejected("; ".join(review.reasons) or "drawing rejected")
    return review


def companion_request(
    spec: CompanionSpec,
    review: DrawingReview,
    cleaned_png: bytes,
    style: ArtStyle,
    option: int,
    round_: int = 1,  # the parent's redraws get new seeds (round 1 keeps the original ones)
) -> ImageRequest:
    h = house_style()
    prompt = prompts.render(
        "companion_sheet",
        version=2,
        name=spec.name,
        type_label=type_label(spec),
        key_features=review.key_features,
        description=review.description_en,
        traits=spec.traits,
        style=h.style,
        medium=style.guide,
        negative=h.negative,
    )
    ref = RefImage(cleaned_png, sniff_mime(cleaned_png), "the child's original drawing")
    return ImageRequest(
        step=f"companion:option{option}",
        prompt=prompt,
        refs=[ref],
        aspect="3:2",
        seed=1000 * round_ + option,
    )


@dataclass
class CompanionOptions:
    spec: CompanionSpec  # description_en filled from the drawing review
    review: DrawingReview
    options: list[GeneratedImage]


async def generate_companion_options(
    rt: Runtime, cleaned_png: bytes, spec: CompanionSpec, style: ArtStyle, n: int = 2, round_: int = 1
) -> CompanionOptions:
    review = await review_drawing(rt, cleaned_png, spec)
    spec = spec.model_copy(update={"description_en": review.description_en, "from_drawing": True})
    options = await asyncio.gather(
        *(rt.draw(companion_request(spec, review, cleaned_png, style, i + 1, round_)) for i in range(n))
    )
    return CompanionOptions(spec=spec, review=review, options=list(options))


async def score_fidelity(rt: Runtime, drawing_png: bytes, sheet: GeneratedImage) -> CompanionFidelity:
    return await rt.ask(
        step="companion:fidelity",
        system=prompts.render("companion_fidelity"),
        user=[
            ImagePart(drawing_png, "image/png"),
            ImagePart(sheet.data, sheet.mime),
            "Reference 1 is the drawing, reference 2 the generated character.",
        ],
        schema=CompanionFidelity,
        fast=True,
    )
