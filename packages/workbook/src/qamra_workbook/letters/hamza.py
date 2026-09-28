"""ء and ى. The hamza stands alone on the line (isolated only); ى is the body of ي without its dots
(isolated and final)."""

from __future__ import annotations

from qamra_workbook.letters.ba import YA, YA_FINAL
from qamra_workbook.letters.hand import final, isolated

# ء: a small head like the head of ع (from its top right, round to the left and back), then a tail down to
# the left onto the line.
HAMZA = "M64 56 C56 46 38 48 36 62 C34 74 50 80 66 74 C58 84 42 92 24 96"

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
