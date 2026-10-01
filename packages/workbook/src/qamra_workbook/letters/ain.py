"""ع غ: an open head, then (isolated, final) a big tail under the line opening to the right; غ has a dot
over the head. The isolated and initial head starts at its top right and turns left and down; in medial
and final forms the head is a small closed loop: up to the left, across, and back down to the line.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one

# isolated ع: the head from its top right round to the left and back to the right, then the tail.
AIN = (
    "M94 52 C84 42 62 42 54 56 C46 70 60 90 84 94 "
    "C62 98 44 108 40 126 C36 146 58 156 86 155 C104 154 118 150 132 142"
)
# initial عـ: the same head, then back along the line to the join.
AIN_INITIAL = "M86 50 C76 40 54 40 46 54 C38 68 48 86 68 90 C74 91 80 91 84 90 C78 95 70 97 60 97 L0 97"
# medial ـعـ: arrives on the line, up to the left, across the top, back down to the line, on to the join.
AIN_MEDIAL = (
    "M92 97 L62 97 C58 97 56 96 54 94 C46 84 38 70 36 60 C35 54 40 52 46 52 C58 52 70 54 72 60 "
    "C74 68 62 84 54 94 C51 96 46 97 40 97 L0 97"
)
# final ـع: the same small head, then down into the tail.
AIN_FINAL = (
    "M150 97 L118 97 C114 97 112 96 110 94 C102 84 94 70 92 60 C91 54 96 52 102 52 C114 52 126 54 128 60 "
    "C130 68 118 84 110 94 C100 106 78 114 72 128 C68 146 88 156 114 155 C128 154 138 150 146 144"
)

LETTERS = tuple(
    shape
    for char, dot in (("ع", False), ("غ", True))
    for shape in (
        isolated(char, 150, AIN, dots=one(74, 22) if dot else ()),
        initial(char, 100, AIN_INITIAL, dots=one(66, 20) if dot else ()),
        medial(char, 92, AIN_MEDIAL, dots=one(54, 28) if dot else ()),
        final(char, 150, AIN_FINAL, dots=one(110, 28) if dot else ()),
    )
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ع": (
        "من أعلى الرأس يمينًا نلفّ إلى اليسار ثم نرجع إلى اليمين، ثم ننزل إلى اليسار في بطن كبير "
        "تحت السطر ونخرج إلى اليمين. في وسط الكلمة وآخرها الرأس حلقة صغيرة مغلقة."
    ),
    "غ": ("مثل العين، ثم نقطة فوق الرأس."),
}
