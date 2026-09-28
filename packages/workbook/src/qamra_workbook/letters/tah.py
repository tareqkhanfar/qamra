"""ط ظ: the loop of ص and a short base, then the stick from the top line down onto the loop; ظ has a dot
to the right of the stick. The body comes first, the stick second (like the head of the medial kaf)."""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, one

# isolated ط: the loop from its neck, back along the line and a little further left.
TAH = "M74 96 C82 76 106 60 130 60 C150 60 160 72 154 85 C149 95 134 97 118 97 L36 97 C30 97 26 95 24 90"
# initial طـ: the loop from its neck, back along the line to the join.
TAH_INITIAL = "M60 96 C68 76 92 60 116 60 C136 60 146 72 140 85 C135 95 120 97 104 97 L0 97"
# medial ـطـ: arrives on the line under the loop to its neck, round the loop and on to the join.
TAH_MEDIAL = (
    "M176 97 L62 97 C70 76 94 60 118 60 C138 60 148 72 142 85 C137 94 122 95 106 95 L64 95 "
    "C56 95 50 97 42 97 L0 97"
)
# final ـط: the same, ending on the line like the isolated one.
TAH_FINAL = (
    "M180 97 L64 97 C72 76 96 60 120 60 C140 60 150 72 144 85 C139 94 124 95 108 95 L66 95 "
    "C58 95 52 97 44 97 L32 97 C26 97 22 95 20 90"
)


def stick(x: float) -> str:
    """The stick, from the top line straight down onto the neck of the loop."""
    return f"M{x} -25 L{x - 2} 90"


LETTERS = tuple(
    shape
    for char, dot in (("ط", False), ("ظ", True))
    for shape in (
        isolated(char, 170, TAH, stick(82), dots=one(114, 34) if dot else ()),
        initial(char, 160, TAH_INITIAL, stick(68), dots=one(100, 34) if dot else ()),
        medial(char, 176, TAH_MEDIAL, stick(70), dots=one(102, 34) if dot else ()),
        final(char, 180, TAH_FINAL, stick(72), dots=one(104, 34) if dot else ()),
    )
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ط": (
        "أولًا الحلقة: من السطر نصعد وندور إلى اليمين مع عقارب الساعة ونرجع على السطر. ثانيًا "
        "العصا: من السطر العلوي ننزل حتى الحلقة."
    ),
    "ظ": ("مثل الطاء، ثم نقطة على يمين العصا."),
}
