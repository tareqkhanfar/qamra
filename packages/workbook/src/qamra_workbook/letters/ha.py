"""ه ة: ه has a shape of its own in each place; ة is the isolated or final ه with two dots on top.

- isolated and initial: from the top point down the left side, along the line, up the right side back to
  the top, then down the middle (and on along the line to the join);
- medial: a tall loop over the line and a small one under it;
- final: up from the line to the top point, down the left side and back along the line.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, two

# isolated ه: from the top point down the left side, along the line, up the right side back to the top,
# then down the middle.
HA = (
    "M58 44 C44 52 32 70 32 84 C32 94 40 97 52 97 L70 97 C84 97 92 88 90 74 C88 58 76 46 58 44 "
    "C54 60 52 78 52 94"
)
# initial هـ: the same, and on from the middle along the line to the join.
HA_INITIAL = (
    "M64 44 C50 52 38 70 38 84 C38 93 44 96 56 96 L76 96 C90 96 98 88 96 74 C94 58 82 46 64 44 "
    "C60 60 58 76 56 88 C54 95 48 97 40 97 L0 97"
)
# medial ـهـ: arrives on the line, up the right side of the tall loop, down its left side and under the
# line round the small loop, back up and on to the join.
HA_MEDIAL = (
    "M80 97 L64 97 C58 97 56 92 54 84 C51 72 48 60 46 50 C42 62 36 76 36 90 "
    "C36 108 40 124 52 126 C62 128 66 116 60 106 C54 98 44 97 36 97 L0 97"
)
# final ـه: arrives on the line, up to the top point, down the left side, back along the line.
HA_FINAL = "M92 97 L68 97 C63 97 61 93 61 86 L60 48 C46 56 34 70 34 84 C34 94 44 97 56 97 L66 97"

LETTERS = (
    isolated("ه", 104, HA),
    initial("ه", 104, HA_INITIAL),
    medial("ه", 80, HA_MEDIAL),
    final("ه", 92, HA_FINAL),
    isolated("ة", 104, HA, dots=two(60, 20)),
    final("ة", 92, HA_FINAL, dots=two(52, 24)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ه": (
        "منفصلة وفي أول الكلمة: من الرأس ننزل يسارًا، نمشي على السطر، نصعد يمينًا ونرجع إلى الرأس، "
        "ثم ننزل في الوسط. في وسط الكلمة حلقتان: فوق السطر وتحته. في آخرها نصعد من السطر وننزل "
        "يسارًا ونرجع على السطر."
    ),
    "ة": ("مثل الهاء المنفصلة أو في آخر الكلمة، ثم نقطتان فوقها: اليمنى أولًا."),
}
