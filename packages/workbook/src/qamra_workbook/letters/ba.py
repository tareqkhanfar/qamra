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

# The tail of ب ت ث (and of ف ك): from the line it curls up on the left to about the tooth line, so the
# isolated and final forms never read as the initial «بـ».
TAIL = "L68 97 C44 98 26 93 21 77 C18 67 19 55 23 44"
# isolated ب ت ث: from the top of the right tooth down, along the bowl to the left and up into the tail.
BOWL = f"M176 36 C177 56 180 78 169 88 C159 96 147 97 130 97 {TAIL}"
# final ـب ـت ـث: arrives on the right, up the tooth and back down, then the same bowl.
BOWL_FINAL = f"M200 97 L192 97 C184 97 179 93 178 85 L176 36 L173 84 C171 94 160 97 144 97 {TAIL}"
# initial بـ تـ ثـ نـ يـ: down the tooth, then left along the line to the join.
TOOTH_INITIAL = "M56 36 C57 58 59 79 51 89 C45 95 37 97 27 97 L0 97"
# medial ـبـ ـتـ ـثـ ـنـ ـيـ: arrives on the right, up the tooth and back down, on to the left join.
TOOTH_MEDIAL = "M64 97 L50 97 C42 97 36 93 35 85 L32 36 L29 85 C28 93 22 97 14 97 L0 97"
# isolated ن: down the right horn into a round bowl under the line, up to the line on the left. The bowl is
# about two thirds of the tooth height deep: less than the bowl of ق (`fa.QAF`), as in print.
NOON = "M104 40 C105 64 107 90 104 106 C100 128 84 140 62 140 C40 140 24 128 22 110 C21 102 23 96 27 90"
# final ـن: arrives on the right, up the horn and back down into the same bowl.
NOON_FINAL = (
    "M150 97 L142 97 C134 97 129 93 128 85 L126 40 L123 84 C122 96 121 104 118 112 "
    "C112 130 96 140 76 140 C54 140 38 128 36 110 C35 102 37 96 41 90"
)
# isolated ي: a small head curling left, down across to the right, then a shallow wide belly just under the
# line, ending up on the left. The two dots go under the belly (as in print and school handwriting), so it
# stays shallow enough for them to fit above the descender line.
YA = (
    "M122 50 C108 42 88 48 88 62 C88 76 104 82 118 90 C132 98 137 110 127 118 "
    "C115 127 92 128 66 126 C42 124 26 116 22 100 C21 95 22 91 24 87"
)
# final ـي: arrives on the right, turns sharply back down to the right, then the same belly to the left.
YA_FINAL = (
    "M150 97 L98 97 C106 102 118 106 124 113 C130 121 122 128 100 129 "
    "C76 131 46 130 32 122 C22 116 21 104 26 94"
)
UNDER_YA = 146  # the two dots under the belly of the isolated and final ي

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
    isolated("ن", 130, NOON, dots=one(63, 72)),
    initial("ن", 80, TOOTH_INITIAL, dots=one(50, OVER_TOOTH)),
    medial("ن", 64, TOOTH_MEDIAL, dots=one(32, OVER_TOOTH)),
    final("ن", 150, NOON_FINAL, dots=one(77, 72)),
    isolated("ي", 150, YA, dots=two(78, UNDER_YA)),
    initial("ي", 80, TOOTH_INITIAL, dots=two(42, BELOW)),
    medial("ي", 64, TOOTH_MEDIAL, dots=two(32, BELOW)),
    final("ي", 150, YA_FINAL, dots=two(78, UNDER_YA + 1)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ب": (
        "من رأس السنّ ننزل إلى السطر ونمشي عليه إلى اليسار ثم نرفع الطرف إلى أعلى، "
        "ونضع النقطة تحت الحرف في النهاية. "
        "في وسط الكلمة وآخرها يأتي القلم على السطر فنصعد إلى السنّ ثم ننزل."
    ),
    "ت": ("مثل الباء تمامًا، ثم نقطتان فوقه: اليمنى أولًا."),
    "ث": ("مثل الباء تمامًا، ثم ثلاث نقاط فوقه: اثنتان من اليمين إلى اليسار، ثم الثالثة فوقهما."),
    "ن": (
        "من رأس السنّ ننزل في بطن مستدير تحت السطر ونصعد إلى السطر، والنقطة فوق البطن في النهاية. "
        "في أول الكلمة ووسطها سنّ مثل الباء والنقطة فوقها."
    ),
    "ي": (
        "نبدأ من الأعلى برأس صغير يلتفّ إلى اليسار، ثم نعبر إلى اليمين وننزل في بطن واسع تحت السطر إلى "
        "اليسار. النقطتان تحت البطن: اليمنى أولًا. في أول الكلمة ووسطها سنّ مثل سنّ الباء ونقطتان "
        "تحتها."
    ),
}
