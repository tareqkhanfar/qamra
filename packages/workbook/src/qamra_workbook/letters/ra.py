"""ر ز: a curve from just above the line down to the left, under it; ز has a dot over the head. They never
join the next letter, so they have isolated and final forms only."""

from __future__ import annotations

from qamra_workbook.letters.hand import final, isolated, one

# isolated ر: from the head down, curving to the left under the line.
RA = "M72 60 C75 74 76 90 70 104 C62 122 44 136 20 142"
# final ـر: arrives on the line and goes on down into the same curve.
RA_FINAL = "M104 97 L84 97 C78 97 74 99 72 105 C66 122 46 136 22 142"

LETTERS = (
    isolated("ر", 92, RA),
    final("ر", 104, RA_FINAL),
    isolated("ز", 92, RA, dots=one(70, 34)),
    final("ز", 104, RA_FINAL, dots=one(76, 70)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ر": ("من فوق السطر بقليل ننزل بقوس إلى اليسار حتى تحت السطر."),
    "ز": ("مثل الراء، ثم نقطة فوقها."),
}
