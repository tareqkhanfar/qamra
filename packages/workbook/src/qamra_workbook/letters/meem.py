"""م: a round head on the line (a loop from its neck, up and round clockwise), then a straight tail down
under the line (isolated, final) or the line to the join (initial, medial). In medial and final forms the
pen arrives along the line under the head to its neck.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial

# isolated م: the head from its neck, back along the line a little, then straight down.
MEEM = "M66 96 C55 92 52 78 58 69 C65 58 86 58 90 71 C94 85 83 96 68 97 L46 97 C37 97 33 101 33 110 L33 150"
# initial مـ: the head from its neck, then along the line to the join.
MEEM_INITIAL = "M52 96 C41 92 38 78 44 69 C51 58 72 58 76 71 C80 85 69 96 54 97 L0 97"
# medial ـمـ: arrives on the line under the head to its neck, round the head, on to the join.
MEEM_MEDIAL = (
    "M92 97 L56 97 C45 92 42 78 48 69 C55 58 76 58 80 71 C84 85 74 94 60 95 C54 95 48 96 40 97 L0 97"
)
# final ـم: arrives under the head, round it, then straight down.
MEEM_FINAL = (
    "M124 97 L68 97 C57 92 54 78 60 69 C67 58 88 58 92 71 C96 85 86 94 72 95 C64 95 56 96 48 97 "
    "C39 97 35 101 35 110 L35 150"
)

LETTERS = (
    isolated("م", 108, MEEM),
    initial("م", 86, MEEM_INITIAL),
    medial("م", 92, MEEM_MEDIAL),
    final("م", 124, MEEM_FINAL),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "م": (
        "من السطر نصعد ونرسم الرأس مع عقارب الساعة ونرجع، ثم ننزل بخط مستقيم تحت السطر. في أول "
        "الكلمة ووسطها نكمل على السطر."
    ),
}
