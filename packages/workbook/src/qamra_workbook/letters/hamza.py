"""ء and ى. The hamza stands alone on the line (isolated only); ى is the body of ي without its dots
(isolated and final)."""

from __future__ import annotations

from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.letters.ba import YA, YA_FINAL
from qamra_workbook.letters.hand import final, isolated

# ء: a small head like the head of ع (from its top right, round to the left and back), then a tail down to
# the left onto the line.
HAMZA = "M64 56 C56 46 38 48 36 62 C34 74 50 80 66 74 C58 84 42 92 24 96"

# The hamza over or under a letter (أ إ ؤ ئ) is the lone ء at this scale: about 32 × 35 units, a little under
# a third of the alif, as in a printed naskh. Smaller, its head closed up into a blob on the big letter and
# its few tracing dots read like a damma on the small ones.
HAMZA_MARK = 0.75
MARK_GAP = 12.0  # between the hamza and the alif it sits on (or under)


def hamza_mark(cx: float, *, bottom: float | None = None, top: float | None = None) -> Stroke:
    """The ء stroke as a mark (`HAMZA_MARK`), centred across on x = `cx`, with its lowest point at `bottom`
    or its highest point at `top` (letter units)."""
    x0, y0, x1, y1 = bounds([Stroke(HAMZA)])
    s = HAMZA_MARK
    dy = bottom - y1 * s if bottom is not None else (top if top is not None else 0.0) - y0 * s
    return Stroke(HAMZA).scaled(s, cx - (x0 + x1) / 2 * s, dy)


LETTERS = (
    isolated("ء", 84, HAMZA),
    isolated("ى", 150, YA),
    final("ى", 150, YA_FINAL),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ء": ("رأس صغير: من أعلاه يمينًا نلفّ إلى اليسار ونرجع، ثم ذيل مائل إلى السطر."),
    "ى": ("مثل الياء بلا نقاط."),
}
