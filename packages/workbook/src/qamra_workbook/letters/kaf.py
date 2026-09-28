"""ك ل: tall letters. ل is a stem into the bowl of ن (isolated, final) or onto the line (initial, medial).
ك isolated and final: the stem onto a flat base with a tail, then the small kaf mark inside (a little
hamza). ك initial: one stroke, the slanted head down to the middle, back down to the line and along it.
ك medial: the line first, then the head drawn down onto it.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial

# isolated ل: down the stem, round the bowl under the line, up on the left.
LAM = "M104 -25 L104 94 C104 124 90 146 66 148 C42 150 26 136 24 114 C23 104 25 97 29 91"
# initial لـ: down the stem and along the line to the join.
LAM_INITIAL = "M34 -25 L34 84 C34 93 28 97 18 97 L0 97"
# medial ـلـ: arrives on the line, up the stem and back down, on to the join.
LAM_MEDIAL = "M64 97 L50 97 C43 97 40 94 39 88 L37 -25 L34 86 C33 94 28 97 18 97 L0 97"
# final ـل: arrives on the line, up the stem and back down into the bowl.
LAM_FINAL = (
    "M140 97 L124 97 C117 97 114 94 113 88 L111 -25 L108 94 C108 124 94 146 70 148 "
    "C46 150 30 136 28 114 C27 104 29 97 33 91"
)
# isolated ك: down the stem, along the base and up into the tail; then the mark.
KAF = "M146 -25 L146 82 C146 93 140 97 128 97 L60 97 C42 97 28 93 24 72"
KAF_MARK = "M104 44 C98 38 84 40 84 48 C84 56 96 58 104 55 C98 62 88 66 80 68"
# final ـك: arrives on the line, up the stem and back down, then the same base, tail and mark.
KAF_FINAL = (
    "M180 97 L166 97 C159 97 156 94 155 88 L153 -25 L150 84 C150 93 144 97 132 97 L60 97 C42 97 28 93 24 72"
)
# initial كـ: the head from its top right down to the middle, back down to the line, then along it.
KAF_INITIAL = "M100 -20 C82 -6 58 16 40 36 C56 54 76 72 88 86 C92 92 88 97 80 97 L0 97"
# medial ـكـ: the line from join to join, then the head drawn down onto it.
KAF_MEDIAL = "M100 97 L0 97"
KAF_MEDIAL_HEAD = "M92 -20 C74 -6 50 16 32 36 C48 54 66 72 78 88 C80 92 79 95 76 97"

LETTERS = (
    isolated("ك", 168, KAF, KAF_MARK),
    initial("ك", 110, KAF_INITIAL),
    medial("ك", 100, KAF_MEDIAL, KAF_MEDIAL_HEAD),
    final("ك", 180, KAF_FINAL, KAF_MARK),
    isolated("ل", 128, LAM),
    initial("ل", 58, LAM_INITIAL),
    medial("ل", 64, LAM_MEDIAL),
    final("ل", 140, LAM_FINAL),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ك": (
        "منفصلة وفي آخر الكلمة: العصا من السطر العلوي، ثم نمشي على السطر ونرفع الطرف، وبعدها الهمزة "
        "الصغيرة في الداخل. في أول الكلمة: الرأس المائل ثم نرجع إلى السطر في خط واحد. في وسطها: "
        "الخط على السطر أولًا، ثم الرأس."
    ),
    "ل": (
        "من السطر العلوي ننزل بخط مستقيم، ثم بطن تحت السطر ونصعد إلى اليسار. في أول الكلمة ووسطها "
        "نكمل على السطر."
    ),
}
