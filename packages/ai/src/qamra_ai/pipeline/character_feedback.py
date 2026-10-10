"""«ما الذي لا يشبهه؟» in the parent's own words (Tareq, 2026-10-10): a short free-text note beside the chips.

The note is the parent's text, so it never goes into an image prompt as it is. It first gets the instant local
screen of the custom-story brief (links, phone numbers, plainly unsafe words), then Claude (the fast model,
prompts character_feedback.v1) keeps only what is about how the child looks and rewrites it as a short
English instruction for the character-sheet redraw. A note that is unsafe, or says nothing about the child's
looks, is dropped without bothering the parent, and so is one the text provider could not read: the redraw
then uses the chips alone. The outcome is logged by the caller, never the note itself.
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.pipeline.custom_story import screen_text
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime

NOTE_MAX = 200  # characters the parent can write (the API refuses longer, the form stops there)
INSTRUCTION_MAX = 300  # the redraw prompt never gets more than this from a note
PROMPT_VERSION = 1  # character_feedback.v1 + character_feedback_user.v1

Outcome = Literal["used", "screened", "unsafe", "off_topic", "failed"]


class AppearanceFeedback(BaseModel):
    """Claude's reading of the note (character_feedback.v1)."""

    safe: bool
    about_appearance: bool
    instruction: str = ""  # English, about the child's looks only; "" when nothing is kept


@dataclass(frozen=True)
class NoteResult:
    instruction: str | None  # what the redraw prompt gets; None: the note is ignored
    outcome: Outcome
    reasons: list[str] = field(default_factory=list)  # why the local screen stopped it, or the error's type


def clean_note(text: str | None) -> str | None:
    """The note as it is kept: whitespace squashed, None when empty."""
    if text is None:
        return None
    return " ".join(text.split()) or None


async def appearance_instruction(rt: Runtime, child: Child, note: str) -> NoteResult:
    """The note → a short appearance-only instruction for the redraw, or why it is ignored."""
    reasons = screen_text(note)
    if reasons:
        return NoteResult(None, "screened", reasons)
    # the note sits between tags in the prompt: it can't close them
    quoted = note.replace("<", "‹").replace(">", "›")
    try:
        out = await rt.ask(
            step="character:feedback",
            system=prompts.render("character_feedback", version=PROMPT_VERSION),
            user=[
                prompts.render(
                    "character_feedback_user",
                    version=PROMPT_VERSION,
                    age=child.age,
                    gender=child.gender,
                    hijab=child.hijab,
                    glasses=child.glasses,
                    note=quoted,
                )
            ],
            schema=AppearanceFeedback,
            fast=True,
            max_tokens=600,
        )
    except Exception as e:  # any failure of the text step: the redraw goes ahead with the chips alone
        return NoteResult(None, "failed", [type(e).__name__])
    if not out.safe:
        return NoteResult(None, "unsafe")
    instruction = " ".join(out.instruction.split())[:INSTRUCTION_MAX]
    if not out.about_appearance or not instruction:
        return NoteResult(None, "off_topic")
    found = screen_text(instruction)  # the rewrite gets the same screen as the note
    if found:
        return NoteResult(None, "screened", found)
    return NoteResult(instruction, "used")
