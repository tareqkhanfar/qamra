"""د ذ: a short head leaning left, then along the line; ذ has a dot over the head. They never join the next
letter, so they have isolated and final forms only."""

from __future__ import annotations

from qamra_workbook.letters.hand import final, isolated, one

# isolated د: from the top of the head down to the right, round onto the line and along it to the left.
DAL = "M58 44 C66 58 78 74 82 86 C84 94 78 97 68 97 L32 97 C26 97 22 95 20 90"
# final ـد: arrives on the line, climbs the head and comes back down beside it, then along the line.
DAL_FINAL = (
    "M126 97 L104 97 C98 97 95 94 94 90 C88 76 78 60 70 46 C80 58 90 74 90 86 "
    "C90 94 84 97 74 97 L38 97 C32 97 28 95 26 90"
)

LETTERS = (
    isolated("د", 100, DAL),
    final("د", 126, DAL_FINAL),
    isolated("ذ", 100, DAL, dots=one(52, 20)),
    final("ذ", 126, DAL_FINAL, dots=one(64, 22)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "د": (
        "من أعلى الرأس ننزل مائلين إلى اليمين حتى السطر، ثم نمشي عليه إلى اليسار. في آخر الكلمة "
        "نصعد إلى الرأس ثم ننزل."
    ),
    "ذ": ("مثل الدال، ثم نقطة فوق الرأس."),
}
