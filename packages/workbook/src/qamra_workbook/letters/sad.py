"""ص ض: a long loop, a small tooth, then (isolated, final) the bowl of ن; ض has a dot over the loop.

The loop starts at its neck on the line, goes up and round clockwise and comes back along the line. In
medial and final forms the pen arrives along the line, under the loop, to its neck.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one
from qamra_workbook.letters.seen import bowl

# isolated ص: the loop from its neck, the small tooth, then down round the bowl.
SAD = (
    "M152 96 C160 76 184 60 208 60 C228 60 238 72 232 85 C227 95 212 97 196 97 L150 97 "
    f"C145 97 142 94 141 88 L139 62 L137 88 {bowl(137)}"
)
# initial صـ: the loop from its neck, the small tooth, then along the line to the join.
SAD_INITIAL = (
    "M72 96 C80 76 104 60 128 60 C148 60 158 72 152 85 C147 95 132 97 116 97 L70 97 "
    "C65 97 62 94 61 88 L59 62 L57 88 C56 94 51 97 43 97 L0 97"
)
# medial ـصـ: arrives on the line under the loop to its neck, round the loop, the tooth, on to the join.
SAD_MEDIAL = (
    "M186 97 L74 97 C82 76 106 60 130 60 C150 60 160 72 154 85 C149 94 134 95 118 95 L76 95 "
    "C67 95 64 93 63 88 L61 62 L59 88 C58 94 53 97 45 97 L0 97"
)
# final ـص: arrives on the line under the loop to its neck, round the loop, the tooth, then the bowl.
SAD_FINAL = (
    "M268 97 L154 97 C162 76 186 60 210 60 C230 60 240 72 234 85 C229 94 214 95 198 95 L156 95 "
    f"C147 95 144 93 143 88 L141 62 L139 88 {bowl(139)}"
)

LETTERS = (
    isolated("ص", 250, SAD),
    initial("ص", 170, SAD_INITIAL),
    medial("ص", 186, SAD_MEDIAL),
    final("ص", 268, SAD_FINAL),
    isolated("ض", 250, SAD, dots=one(192, 36)),
    initial("ض", 170, SAD_INITIAL, dots=one(112, 36)),
    medial("ض", 186, SAD_MEDIAL, dots=one(114, 36)),
    final("ض", 268, SAD_FINAL, dots=one(194, 36)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ص": (
        "من السطر نصعد ونرسم الحلقة إلى اليمين مع عقارب الساعة ونرجع على السطر، ثم سنّ صغيرة، ثم "
        "بطن مستديرة تحت السطر."
    ),
    "ض": ("مثل الصاد، ثم نقطة فوق الحلقة."),
}
