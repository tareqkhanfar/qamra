"""و: a round closed head sitting on the line (about as tall as the tooth line), then a long tail that goes
down from its right side and sweeps to the left under the line. It never joins the next letter, so it has
isolated and final forms only.

The head is round and the tail starts under its right side and ends well to the left of it: a narrow head
on a short slanted tail reads as «ر».
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, isolated

# isolated و: from the neck on the line at the head's lower right, left along its bottom, up its left side,
# round the top clockwise, down its right side through the neck, then the tail down and to the left.
WAW = (
    "M82 96 C72 99 56 99 49 89 C42 79 43 61 54 53 C65 45 83 47 89 60 C94 72 90 87 83 97 "
    "C80 110 77 122 68 132 C57 143 38 148 16 148"
)
# final ـو: arrives along the line to the neck, then the same head and tail.
WAW_FINAL = (
    "M124 97 L86 97 C76 99 60 99 53 89 C46 79 47 61 58 53 C69 45 87 47 93 60 C98 72 94 87 87 97 "
    "C84 110 81 122 72 132 C61 143 42 148 20 148"
)

LETTERS = (
    isolated("و", 104, WAW),
    final("و", 124, WAW_FINAL),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "و": (
        "من السطر نرسم رأسًا مستديرًا باتجاه عقارب الساعة ونغلقه، ثم ننزل بذيل طويل تحت السطر "
        "ونسحبه إلى اليسار."
    ),
}
