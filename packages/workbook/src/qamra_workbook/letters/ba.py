"""ب ت ث ن ي: one body per form, told apart by their dots. The initial and medial forms of all five are the
same tooth; the isolated and final ب ت ث share the ب bowl; ن and ي have their own isolated and final bowls.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import (
    ABOVE,
    BELOW,
    OVER_TOOTH,
    final,
    initial,
    isolated,
    medial,
    one,
    three,
    two,
)

# isolated ب ت ث: from the top of the right tooth down, along the bowl to the left and up into the tail
# (the sample ب, unchanged).
BOWL = "M176 36 C177 56 180 78 169 88 C159 96 147 97 130 97 L62 97 C42 97 27 93 22 70"
# final ـب ـت ـث: arrives on the right, up the tooth and back down, then the same bowl.
BOWL_FINAL = (
    "M200 97 L192 97 C184 97 179 93 178 85 L176 36 L173 84 C171 94 160 97 144 97 L62 97 C42 97 27 93 22 70"
)
# initial بـ تـ ثـ نـ يـ: down the tooth, then left along the line to the join.
TOOTH_INITIAL = "M56 36 C57 58 59 79 51 89 C45 95 37 97 27 97 L0 97"
# medial ـبـ ـتـ ـثـ ـنـ ـيـ: arrives on the right, up the tooth and back down, on to the left join.
TOOTH_MEDIAL = "M64 97 L50 97 C42 97 36 93 35 85 L32 36 L29 85 C28 93 22 97 14 97 L0 97"
# isolated ن: down the right horn into a round bowl under the line, up to the line on the left.
NOON = "M104 40 C105 66 108 94 104 112 C99 136 82 148 62 148 C40 148 24 134 22 112 C21 104 23 97 27 91"
# final ـن: arrives on the right, up the horn and back down into the same bowl.
NOON_FINAL = (
    "M150 97 L142 97 C134 97 129 93 128 85 L126 40 L123 84 C122 96 122 104 118 116 "
    "C112 138 96 148 76 148 C54 148 38 134 36 112 C35 104 37 97 41 91"
)
# isolated ي: a small head curling left, down across to the right, then the wide belly under the line,
# ending up on the left.
YA = (
    "M122 52 C108 44 88 50 88 64 C88 78 104 84 118 92 C132 100 138 116 130 130 "
    "C120 146 92 150 66 148 C42 146 24 136 22 114 C21 106 23 100 26 94"
)
# final ـي: arrives on the right, turns sharply back down to the right, then the same belly to the left.
YA_FINAL = (
    "M150 97 L98 97 C106 104 120 112 126 124 C132 136 124 147 100 149 "
    "C76 151 46 150 32 141 C22 134 21 114 26 100"
)

LETTERS = (
    isolated("ب", 200, BOWL, dots=one(100, BELOW)),
    initial("ب", 80, TOOTH_INITIAL, dots=one(44, BELOW)),
    medial("ب", 64, TOOTH_MEDIAL, dots=one(32, BELOW)),
    final("ب", 200, BOWL_FINAL, dots=one(100, BELOW)),
    isolated("ت", 200, BOWL, dots=two(100, ABOVE)),
    initial("ت", 80, TOOTH_INITIAL, dots=two(48, OVER_TOOTH)),
    medial("ت", 64, TOOTH_MEDIAL, dots=two(32, OVER_TOOTH)),
    final("ت", 200, BOWL_FINAL, dots=two(100, ABOVE)),
    isolated("ث", 200, BOWL, dots=three(100, ABOVE + 2)),
    initial("ث", 80, TOOTH_INITIAL, dots=three(48, OVER_TOOTH + 4)),
    medial("ث", 64, TOOTH_MEDIAL, dots=three(32, OVER_TOOTH + 4)),
    final("ث", 200, BOWL_FINAL, dots=three(100, ABOVE + 2)),
    isolated("ن", 130, NOON, dots=one(63, 70)),
    initial("ن", 80, TOOTH_INITIAL, dots=one(50, OVER_TOOTH)),
    medial("ن", 64, TOOTH_MEDIAL, dots=one(32, OVER_TOOTH)),
    final("ن", 150, NOON_FINAL, dots=one(77, 70)),
    isolated("ي", 150, YA, dots=two(70, 121)),
    initial("ي", 80, TOOTH_INITIAL, dots=two(42, BELOW)),
    medial("ي", 64, TOOTH_MEDIAL, dots=two(32, BELOW)),
    final("ي", 150, YA_FINAL, dots=two(72, 126)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ب": (
        "من رأس السنّ ننزل إلى السطر ونمشي عليه إلى اليسار ثم نصعد قليلًا، والنقطة تحته في النهاية. "
        "في وسط الكلمة وآخرها يصل القلم على السطر فنصعد إلى السنّ ثم ننزل."
    ),
    "ت": ("مثل الباء تمامًا، ثم نقطتان فوقه: اليمنى أولًا."),
    "ث": ("مثل الباء تمامًا، ثم ثلاث نقاط فوقه: اثنتان من اليمين إلى اليسار، ثم الثالثة فوقهما."),
    "ن": (
        "من رأس السنّ ننزل في بطن مستديرة تحت السطر ونصعد إلى السطر، والنقطة فوق البطن في النهاية. "
        "في أول الكلمة ووسطها سنّ مثل الباء والنقطة فوقها."
    ),
    "ي": (
        "من الأعلى رأس صغير يلتفّ إلى اليسار، ثم نعبر إلى اليمين وننزل في بطن واسعة تحت السطر إلى "
        "اليسار. النقطتان داخل البطن: اليمنى أولًا. في أول الكلمة ووسطها سنّ مثل الباء ونقطتان "
        "تحتها."
    ),
}
