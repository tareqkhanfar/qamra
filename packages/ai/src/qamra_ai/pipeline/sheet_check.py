"""The character sheet's automatic check before the parent sees it (2026-10-21).

The owner often got sheets where a figure's head and body faced opposite ways: the side view's head in profile
looking right while the body, arms and feet walked left. `character_sheet.v10` names one direction per
view (left, in every style), and this check reads the drawn sheet with the main text model (vision): for each
figure, the way the head, the body and the feet point, and whether both shoes are on and inside the picture.
The code, not the model, decides what is wrong:

- a figure whose head, body or feet point left while another of them points right;
- a figure with a bare foot, or a shoe cut off by the picture's edge;
- not three figures.

Then the sheet is drawn once more with what was wrong (`character_request(..., checks=)`, its own seed), and
checked again; the better of the two is kept (the redraw on a tie). The redraw costs one more sheet ($0.15 on
Nano Banana Pro), only then, and it is logged like any call (`character:N:redraw`). A failed check (no text
provider, an error) keeps the sheet as drawn: it never blocks the parent's drawing.

Cost: one vision call on the main text model per check, about $0.01 (`character:sheet-check`).
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.image.base import sniff_mime
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.text.base import ImagePart, UserPart

PROMPT_VERSION = 1
STEP = "character:sheet-check"
FIGURES = 3
Way = Literal["left", "right", "viewer", "away"]
Outcome = Literal["ok", "redrawn", "redrawn_flawed", "kept_flawed", "failed", "off"]
VIEWS = ("front view", "three-quarter view", "side view")


class FigureCheck(BaseModel):
    head: Way
    body: Way
    feet: Literal["left", "right", "viewer", "away", "mixed"]
    shoes_whole: bool


class SheetCheck(BaseModel):
    """What the model sees, figure by figure from the picture's left (sheet_check.v1)."""

    figures: list[FigureCheck]


def problems(check: SheetCheck) -> list[str]:
    """What is wrong with a sheet, as lines for the redraw's prompt; empty when nothing is."""
    out: list[str] = []
    if len(check.figures) != FIGURES:
        out.append(f"The sheet showed {len(check.figures)} figures: draw exactly three, side by side.")
    for i, fig in enumerate(check.figures[:FIGURES]):
        name = f"Figure {i + 1} ({VIEWS[i]})" if i < len(VIEWS) else f"Figure {i + 1}"
        parts = {"the head": fig.head, "the body": fig.body, "the feet": fig.feet}
        sides = {way for way in parts.values() if way in ("left", "right")}
        if len(sides) > 1 or fig.feet == "mixed":
            said = ", ".join(f"{k} {v}" for k, v in parts.items())
            out.append(
                f"{name} faced two ways ({said}): the head, eyes, chest, hips and feet all turn the same way."
            )
        if not fig.shoes_whole:
            out.append(f"{name} had a bare foot or a shoe cut off by the edge: both shoes on and whole.")
    return out


async def read_sheet(rt: Runtime, sheet: bytes) -> list[str]:
    """The sheet's problems (`problems`); raises when the check itself fails."""
    user: list[UserPart] = [ImagePart(sheet, sniff_mime(sheet)), "Check this character sheet."]
    out = await rt.ask(
        step=STEP,
        system=prompts.render("sheet_check", version=PROMPT_VERSION),
        user=user,
        schema=SheetCheck,
        max_tokens=600,
    )
    return problems(out)


@dataclass(frozen=True)
class SheetVerdict:
    outcome: Outcome
    found: list[str] = field(default_factory=list)  # the first sheet's problems
    left: list[str] = field(default_factory=list)  # the kept sheet's problems
    error: str | None = None  # the failed check's error type

    def to_params(self) -> dict[str, object]:
        """What the character keeps (`params["sheet_check"]`): the outcome and the problems, never images."""
        out: dict[str, object] = {"outcome": self.outcome}
        if self.found:
            out["found"] = self.found
        if self.left:
            out["left"] = self.left
        if self.error:
            out["error"] = self.error
        return out
