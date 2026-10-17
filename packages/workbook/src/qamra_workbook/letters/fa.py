"""ف ق: a head (a loop from its neck on the line, up and round clockwise), then a shallow bowl (ف) or a
deep bowl under the line (ق). ف has one dot over the head, ق two. The initial and medial forms are the
same for both letters; only the dots differ. In medial and final forms the pen arrives along the line
under the head to its neck.

The isolated and final ف end in a shallow bowl that curls up on the left, so they never read as the initial
«فـ». The isolated and final ق have a small round head sitting on the line and a round bowl that
goes deeper under the line than the bowl of ن, so ق never reads as «ن» with a head.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one, two

# isolated ف: the head from its neck, then a shallow round bowl just under the line to the left, curling up
# on the left to about the tooth line (never the initial «فـ»).
FA = (
    "M128 96 C118 90 115 72 121 62 C127 52 143 52 148 62 C153 74 149 90 138 95 C134 97 130 97 124 97 "
    "C98 99 60 104 40 98 C26 94 19 80 20 64 C20 56 21 50 23 44"
)
# initial فـ قـ: the head from its neck, then along the line to the join.
FA_INITIAL = "M52 96 C42 90 39 72 45 62 C51 52 67 52 72 62 C77 74 73 90 62 95 C58 97 54 97 48 97 L0 97"
# medial ـفـ ـقـ: arrives on the line under the head to its neck, round the head, on to the join.
FA_MEDIAL = (
    "M92 97 L56 97 C46 90 43 72 49 62 C55 52 71 52 76 62 C81 74 77 88 66 93 C62 95 58 95 52 95 "
    "C46 95 42 96 36 97 L0 97"
)
# final ـف: arrives under the head, round it, then the same bowl and tail.
FA_FINAL = (
    "M190 97 L130 97 C120 90 117 72 123 62 C129 52 145 52 150 62 C155 74 151 88 140 93 C136 95 132 95 126 95 "
    "C100 97 62 104 42 98 C28 94 21 80 22 64 C22 56 23 50 25 44"
)
# isolated ق: the small head from its neck on the line, round it, then from its foot down the right side of
# a deep round bowl under the line and up on the left.
QAF = (
    "M100 96 C90 91 87 78 91 67 C96 57 112 56 117 66 C121 76 118 89 109 96 "
    "C107 103 105 110 103 118 C99 140 84 153 64 153 C42 153 26 141 24 119 C23 109 25 101 29 95"
)
# final ـق: arrives on the line under the head to its neck, then the same head and bowl.
QAF_FINAL = (
    "M150 97 L114 97 C104 92 101 79 105 68 C110 58 126 57 131 67 C135 77 132 90 123 97 "
    "C120 104 119 111 117 119 C113 141 98 153 78 153 C56 153 40 141 38 119 C37 109 39 101 43 95"
)

LETTERS = (
    isolated("ف", 170, FA, dots=one(135, 32)),
    initial("ف", 84, FA_INITIAL, dots=one(59, 32)),
    medial("ف", 92, FA_MEDIAL, dots=one(63, 32)),
    final("ف", 190, FA_FINAL, dots=one(137, 32)),
    isolated("ق", 130, QAF, dots=two(104, 36)),
    initial("ق", 84, FA_INITIAL, dots=two(59, 32)),
    medial("ق", 92, FA_MEDIAL, dots=two(63, 32)),
    final("ق", 150, QAF_FINAL, dots=two(118, 36)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ف": (
        "من السطر نصعد ونرسم الرأس باتجاه عقارب الساعة ونرجع إلى السطر، "
        "ثم نمشي على السطر إلى اليسار ونرفع الطرف إلى أعلى. النقطة فوق الرأس."
    ),
    "ق": (
        "نرسم رأسًا صغيرًا على السطر مثل رأس الفاء، ثم ننزل في بطن مستدير عميق تحت السطر ونصعد إلى اليسار. "
        "نقطتان فوق الرأس: اليمنى أولًا."
    ),
}
