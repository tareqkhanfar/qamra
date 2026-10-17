"""ج ح خ: the same body in every form; ج has a dot under the head (or in the bowl), خ a dot over the head.

The head is a hat: from its left tip the pen goes right along the top, then turns sharply back down to the
left, on a slant, into the bowl (isolated, final) or onto the line (initial, medial). Under the hat the
letter stays open: the slant meets the line left of the hat's corner, so «حـ» never closes into «د».

In medial and final forms the pen first draws the line from the previous letter (the medial one on to the
next letter, like the medial ك), then lifts and writes the hat from its tip down onto that line.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one

# isolated ح: the hat left to right, then down to the left on a slant, round the bowl under the line, out to
# the right.
HAH = "M40 52 C62 47 86 43 110 44 C88 54 62 72 52 96 C42 120 52 150 86 153 C104 154 120 149 134 141"
# initial حـ: the hat from its tip to the right, then down to the left on a slant onto the line, then along
# the line to the join.
HAH_INITIAL = "M30 50 C52 45 78 41 104 42 C84 52 62 68 52 84 C48 92 42 97 32 97 L0 97"
# medial ـحـ: the line from join to join first, then the hat drawn down onto it.
HAH_MEDIAL = "M104 97 L0 97"
HAH_MEDIAL_HEAD = "M24 50 C46 45 72 41 98 42 C78 52 58 68 48 84 C45 90 43 94 42 97"
# final ـح: the line from the previous letter to the foot of the slant, then the hat and the bowl.
HAH_FINAL = "M154 97 L58 97"
HAH_FINAL_HEAD = (
    "M44 52 C66 47 90 43 114 44 C92 54 66 72 56 96 C46 120 56 150 90 153 C108 154 124 149 138 141"
)

LETTERS = tuple(
    shape
    for char, below, above in (("ج", True, False), ("ح", False, False), ("خ", False, True))
    for shape in (
        isolated(char, 150, HAH, dots=one(88, 120) if below else one(76, 20) if above else ()),
        initial(char, 112, HAH_INITIAL, dots=one(70, 124) if below else one(66, 20) if above else ()),
        medial(
            char,
            104,
            HAH_MEDIAL,
            HAH_MEDIAL_HEAD,
            dots=one(62, 124) if below else one(60, 20) if above else (),
        ),
        final(
            char,
            154,
            HAH_FINAL,
            HAH_FINAL_HEAD,
            dots=one(92, 122) if below else one(80, 20) if above else (),
        ),
    )
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ج": (
        "نبدأ من طرف الرأس الأيسر ونمشي إلى اليمين، ثم ننزل مائلين إلى اليسار وندور تحت السطر "
        "ونخرج إلى اليمين. النقطة داخل البطن في النهاية. في وسط الكلمة وآخرها نرسم الخط على السطر "
        "أولًا، ثم الرأس."
    ),
    "ح": (
        "مثل الجيم بلا نقطة: نرسم الرأس من طرفه الأيسر إلى اليمين، ثم ننزل مائلين إلى اليسار. في أول "
        "الكلمة ووسطها ننزل إلى السطر، وفي الحاء المنفصلة وفي آخر الكلمة ندور تحت السطر ونخرج إلى اليمين."
    ),
    "خ": ("مثل الحاء، ثم نقطة فوق الرأس."),
}
