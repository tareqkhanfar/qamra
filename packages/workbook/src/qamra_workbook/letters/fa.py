"""ف ق: a head (a loop from its neck on the line, up and round clockwise), then the ب bowl (ف) or a deep
bowl under the line (ق). ف has one dot over the head, ق two. The initial and medial forms are the same for
both letters; only the dots differ. In medial and final forms the pen arrives along the line under the
head to its neck.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one, two

# isolated ف: the head from its neck, then along the line to the left and up into the tail (like ب).
FA = "M170 96 C160 90 157 72 163 62 C169 52 185 52 190 62 C195 74 191 90 180 95 C176 97 172 97 166 97 L62 97 C42 97 27 93 22 70"  # noqa: E501
# initial فـ قـ: the head from its neck, then along the line to the join.
FA_INITIAL = "M52 96 C42 90 39 72 45 62 C51 52 67 52 72 62 C77 74 73 90 62 95 C58 97 54 97 48 97 L0 97"
# medial ـفـ ـقـ: arrives on the line under the head to its neck, round the head, on to the join.
FA_MEDIAL = (
    "M92 97 L56 97 C46 90 43 72 49 62 C55 52 71 52 76 62 C81 74 77 88 66 93 C62 95 58 95 52 95 "
    "C46 95 42 96 36 97 L0 97"
)
# final ـف: arrives under the head, round it, then along the line and up into the tail.
FA_FINAL = (
    "M230 97 L172 97 C162 90 159 72 165 62 C171 52 187 52 192 62 C197 74 193 88 182 93 C178 95 174 95 168 95 "
    "C160 95 152 97 142 97 L62 97 C42 97 27 93 22 70"
)
# isolated ق: the head from its neck, then down round a deep bowl and up on the left.
QAF = (
    "M114 96 C104 90 101 72 107 62 C113 52 129 52 134 62 C139 74 135 90 124 95 C117 98 111 101 107 108 "
    "C100 126 88 146 64 148 C40 150 24 136 22 114 C21 104 23 97 27 91"
)
# final ـق: arrives under the head, round it, then the same deep bowl.
QAF_FINAL = (
    "M164 97 L128 97 C118 90 115 72 121 62 C127 52 143 52 148 62 C153 74 149 88 138 93 "
    "C131 96 125 99 121 106 C114 126 102 146 78 148 C54 150 38 136 36 114 C35 104 37 97 41 91"
)

LETTERS = (
    isolated("ف", 212, FA, dots=one(177, 32)),
    initial("ف", 84, FA_INITIAL, dots=one(59, 32)),
    medial("ف", 92, FA_MEDIAL, dots=one(63, 32)),
    final("ف", 230, FA_FINAL, dots=one(179, 32)),
    isolated("ق", 150, QAF, dots=two(121, 32)),
    initial("ق", 84, FA_INITIAL, dots=two(59, 32)),
    medial("ق", 92, FA_MEDIAL, dots=two(63, 32)),
    final("ق", 164, QAF_FINAL, dots=two(135, 32)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ف": (
        "من السطر نصعد ونرسم الرأس مع عقارب الساعة ونرجع، ثم نمشي على السطر إلى اليسار ونصعد "
        "قليلًا. النقطة فوق الرأس."
    ),
    "ق": ("الرأس مثل الفاء، ثم بطن مستدير تحت السطر ونصعد إلى اليسار. نقطتان فوق الرأس: اليمنى أولًا."),
}
