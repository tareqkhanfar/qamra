"""و: a small head sitting on the line, then a tail down to the left under it. It never joins the next
letter, so it has isolated and final forms only."""

from __future__ import annotations

from qamra_workbook.letters.hand import final, isolated

# isolated و: from the neck up the left side of the head, round clockwise back to the neck, then the tail.
WAW = (
    "M66 96 C54 90 50 74 58 64 C66 54 84 56 88 70 C92 82 84 92 72 98 "
    "C64 104 56 118 48 128 C40 136 32 140 22 142"
)
# final ـو: arrives on the line under the head, goes round it the same way, then the tail.
WAW_FINAL = (
    "M120 97 L96 97 C86 97 76 97 70 96 C58 90 54 74 62 64 C70 54 88 56 92 70 C96 82 88 92 76 98 "
    "C68 104 60 118 52 128 C44 136 36 140 26 142"
)

LETTERS = (
    isolated("و", 100, WAW),
    final("و", 120, WAW_FINAL),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "و": ("من السطر نصعد ونرسم الرأس مع عقارب الساعة، ثم ننزل بذيل إلى اليسار تحت السطر."),
}
