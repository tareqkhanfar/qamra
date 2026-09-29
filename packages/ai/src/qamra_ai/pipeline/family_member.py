"""A family member's character sheet (Addendum 7 §7, the illustrated-family add-on): 1–3 photos of one
person the parent consented for → one sheet (front + 2 poses), drawn like the child's with the same providers,
and reused by every family book of the child."""

from collections.abc import Sequence
from dataclasses import dataclass

from qamra_ai import prompts
from qamra_ai.image.base import ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import ArtStyle

# the store's relations (qamra_api.store.workbooks.RELATIONS) as the prompt names them
WHO = {
    "mother": "the child's mother",
    "father": "the child's father",
    "grandmother": "the child's grandmother",
    "grandfather": "the child's grandfather",
    "maternal-aunt": "the child's aunt",
    "paternal-aunt": "the child's aunt",
    "maternal-uncle": "the child's uncle",
    "paternal-uncle": "the child's uncle",
    "brother": "the child's brother",
    "sister": "the child's sister",
    "baby": "the child's baby sibling",
    "other": "a member of the child's family",
}
OLDER = ("grandmother", "grandfather")


@dataclass(frozen=True)
class MemberSpec:
    relation: str
    adult: bool
    scarf: bool = False


def age_line(member: MemberSpec) -> str:
    if member.relation == "baby":
        return "They are a baby or a toddler and must look that young."
    if member.relation in OLDER:
        return "They are a grandparent: keep their real age, gently."
    if member.adult:
        return "They are an adult: keep their real age."
    return "They are a child: keep child proportions and their real age."


def member_request(
    member: MemberSpec,
    photos: Sequence[bytes],
    style: ArtStyle,
    attempt: int = 1,
    resolution: Resolution = "1K",
) -> ImageRequest:
    if not 1 <= len(photos) <= 3:
        raise ValueError("a family member's sheet needs 1–3 photos")
    h = house_style()
    prompt = prompts.render(
        "family_member_sheet",
        version=1,
        n_photos=len(photos),
        who=WHO.get(member.relation, WHO["other"]),
        age_line=age_line(member),
        scarf=member.scarf,
        style=h.style,
        medium=style.guide,
        people=h.people,
        negative=h.negative,
    )
    refs = [RefImage(p, sniff_mime(p), f"photo of the family member ({i + 1})") for i, p in enumerate(photos)]
    return ImageRequest(
        step=f"family-member:{attempt}",
        prompt=prompt,
        refs=refs,
        aspect="3:2",
        resolution=resolution,
        seed=attempt * 7907,
    )
