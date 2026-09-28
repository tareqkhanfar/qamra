"""ج ح خ: the same body in every form; ج has a dot under the head (or in the bowl), خ a dot over the head.

The head is a short hat: from its left tip the pen goes right, then turns sharply back down to the left,
into the bowl (isolated, final) or along the line (initial, medial). In medial and final forms the pen
arrives on the line, climbs the hat to its tip and comes back down beside it.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one

# isolated ح: the hat left to right, then down to the left, round the bowl under the line, out to the right.
HAH = "M44 54 C62 50 84 44 106 46 C86 56 60 72 50 96 C40 120 50 150 84 153 C102 154 118 149 132 141"
# initial حـ: the hat from its tip right and down to the line, then back along the line to the join.
HAH_INITIAL = "M28 52 C52 42 82 50 100 84 C102 90 100 96 92 97 L0 97"
# medial ـحـ: arrives on the line, up the hat to its tip, back down under it, on along the line.
HAH_MEDIAL = (
    "M104 97 L86 97 C80 97 80 94 78 90 C64 62 44 48 20 52 C40 56 60 68 70 82 C74 88 72 96 60 97 L0 97"
)
# final ـح: arrives on the line, up the hat and back, then down round the bowl like the isolated one.
HAH_FINAL = (
    "M152 97 L124 97 C118 97 118 94 116 90 C102 62 82 48 58 52 C78 56 96 66 108 86 "
    "C88 96 66 108 58 122 C48 142 62 156 92 156 C108 156 122 151 136 143"
)

LETTERS = tuple(
    shape
    for char, below, above in (("ج", True, False), ("ح", False, False), ("خ", False, True))
    for shape in (
        isolated(char, 150, HAH, dots=one(86, 118) if below else one(74, 22) if above else ()),
        initial(char, 112, HAH_INITIAL, dots=one(58, 124) if below else one(56, 26) if above else ()),
        medial(char, 104, HAH_MEDIAL, dots=one(50, 124) if below else one(46, 28) if above else ()),
        final(char, 152, HAH_FINAL, dots=one(96, 126) if below else one(86, 28) if above else ()),
    )
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ج": (
        "نبدأ من طرف الرأس الأيسر ونمشي قليلًا إلى اليمين، ثم ننزل مائلين إلى اليسار وندور تحت "
        "السطر ونخرج إلى اليمين. النقطة داخل البطن في النهاية."
    ),
    "ح": ("مثل الجيم بلا نقطة: الرأس من طرفه الأيسر إلى اليمين، ثم ننزل وندور تحت السطر ونخرج إلى اليمين."),
    "خ": ("مثل الحاء، ثم نقطة فوق الرأس."),
}
