"""Likeness notes: what the child looks like, in words, before the character is drawn (2026-10-19).

The owner's live test: in the cartoon style the drawing was «طفل مختلف», a generic boy with darker hair, a
rounder face and another smile. A stylized image model simplifies what it is not told about, so the text
model (Claude, with vision) first looks at the framed photo, as the image model gets it, and writes short,
neutral notes on how the child looks: hair (colour with its lighter and darker parts, length, texture,
direction, parting, the front), face shape, eyes (and how they look when smiling), eyebrows, nose, smile,
skin tone in daylight, and marks such as freckles or a dimple. The notes go into the portrait and sheet
prompts of every style (`likeness.v3`, then `likeness.v4`) and are kept on the character
(`params["likeness_notes"]`). Since v2 (2026-10-21) the face note gives the face's proportions (longer than
wide or not, where it is widest, the jaw, the chin's width and length) and calls the cheeks full or the face
round only when the photo shows it: v1's "soft full cheeks and a small rounded chin" was any child's, and the
cartoon and 3D faces came out rounder, wider and younger.

Privacy: appearance only. No name, no identity or resemblance to anyone, no ethnicity or origin, no guess at
the age (the family gave it), nothing about the body, the clothes or the place. A hijab and glasses follow the
family's choice, never the photo. The notes get the local text screen, and each is cut to `FIELD_MAX`. Any
failure (the text provider, an unclear photo) leaves the drawing to go ahead without notes.

Cost: one vision call on the main text model, about $0.01 (logged as `character:likeness`).
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.image.base import sniff_mime
from qamra_ai.pipeline.custom_story import screen_text
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.text.base import ImagePart, UserPart

PROMPT_VERSION = 2  # likeness_notes.v2: the face's proportions, no default "round" or "full cheeks"
USER_PROMPT_VERSION = 1  # likeness_notes_user.v1
STEP = "character:likeness"
FIELD_MAX = 220  # characters per note
# The notes in the order the prompts show them, with their labels
FIELDS = (
    ("hair", "Hair"),
    ("face", "Face shape"),
    ("eyes", "Eyes"),
    ("eyebrows", "Eyebrows"),
    ("nose", "Nose"),
    ("mouth", "Mouth and smile"),
    ("skin", "Skin tone"),
    ("marks", "Distinctive marks"),
    ("glasses", "Glasses"),
)

Outcome = Literal["used", "unclear", "screened", "failed"]


class LikenessNotes(BaseModel):
    """Claude's notes (likeness_notes.v1). `clear` is false when the photo doesn't show one child's face
    well enough to describe; then every note is ""."""

    clear: bool
    hair: str = ""
    face: str = ""
    eyes: str = ""
    eyebrows: str = ""
    nose: str = ""
    mouth: str = ""
    skin: str = ""
    marks: str = ""
    glasses: str = ""


@dataclass(frozen=True)
class NotesResult:
    notes: dict[str, str] | None  # field → note, what the prompts get and the character keeps; None: none
    outcome: Outcome
    reasons: list[str] = field(default_factory=list)  # what the screen found, or the error's type


def clean_notes(raw: LikenessNotes, child: Child) -> dict[str, str]:
    """The notes as kept: whitespace squashed, each cut to `FIELD_MAX`, empty ones dropped; the hair only
    without a hijab and the glasses only when the family said so."""
    out: dict[str, str] = {}
    for key, _ in FIELDS:
        if (key == "hair" and child.hijab) or (key == "glasses" and not child.glasses):
            continue
        text = " ".join(str(getattr(raw, key)).split())[:FIELD_MAX].strip()
        if text:
            out[key] = text
    return out


def note_lines(notes: dict[str, str] | None) -> list[str]:
    """`Label: note` lines in a fixed order, for the prompts (unknown keys are ignored)."""
    if not notes:
        return []
    return [f"{label}: {notes[key]}" for key, label in FIELDS if notes.get(key)]


async def likeness_notes(rt: Runtime, child: Child, photos: list[bytes]) -> NotesResult:
    """The framed photo(s) → appearance-only notes for the portrait and sheet prompts, or why none."""
    if not photos:
        return NotesResult(None, "unclear")
    user: list[UserPart] = [ImagePart(p, sniff_mime(p)) for p in photos[:3]]
    user.append(
        prompts.render(
            "likeness_notes_user",
            version=USER_PROMPT_VERSION,
            n_photos=len(user),
            age=child.age,
            gender=child.gender,
            hijab=child.hijab,
            glasses=child.glasses,
        )
    )
    try:
        out = await rt.ask(
            step=STEP,
            system=prompts.render("likeness_notes", version=PROMPT_VERSION),
            user=user,
            schema=LikenessNotes,
            max_tokens=900,
        )
    except Exception as e:  # any failure of the text step: the drawing goes ahead without notes
        return NotesResult(None, "failed", [type(e).__name__])
    if not out.clear:
        return NotesResult(None, "unclear")
    notes = clean_notes(out, child)
    found = sorted({r for text in notes.values() for r in screen_text(text)})
    if found:
        return NotesResult(None, "screened", found)
    return NotesResult(notes or None, "used" if notes else "unclear")
