"""س ش: three small teeth, then (isolated, final) the bowl of ن, wider; ش has three dots over the teeth.

The first tooth of an isolated or initial form is drawn from its top down; every other tooth goes up and
comes back down, with a round valley between teeth.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, initial, isolated, medial, three

PEAK = 60  # the teeth of س are shorter than the ب tooth
STEP = 36  # from one tooth to the next


def teeth(*peaks: float, from_top: bool) -> str:
    """The teeth, right to left: each goes up from the line to its peak and back down, with a round valley
    between two teeth. `from_top`: the stroke starts at the first peak (isolated, initial); otherwise it
    arrives along the line at (peaks[0] + STEP / 2, 97). Ends at the foot of the last tooth."""
    out = [f"M{peaks[0]} {PEAK}"] if from_top else []
    for k, x in enumerate(peaks):
        if k or not from_top:
            out.append(f"C{x + 9} 97 {x + 3} 95 {x + 2} 88 L{x} {PEAK}")
        out.append(f"L{x - 2} 88")
        if k + 1 < len(peaks):
            out.append(f"C{x - 3} 95 {x - 9} 97 {x - 18} 97")
    return " ".join(out)


def on_the_line(x: float) -> str:
    """From the foot of the last tooth at (x, 88) down onto the line and along it to the left join."""
    return f"C{x - 1} 95 {x - 7} 97 {x - 16} 97 L0 97"


def bowl(x: float) -> str:
    """From the foot of the last tooth at (x, 88) down round the bowl under the line, up on the left."""
    return (
        f"C{x - 1} 106 {x - 4} 124 {x - 18} 136 C{x - 32} 148 {x - 58} 150 {x - 78} 148 "
        f"C{x - 98} 146 {x - 112} 134 {x - 114} 114 C{x - 115} 104 {x - 113} 97 {x - 109} 91"
    )


# isolated س: the first tooth from its top, two more teeth, then down round the bowl.
SEEN = f"{teeth(212, 176, 140, from_top=True)} {bowl(138)}"
# initial سـ: the first tooth from its top, two more teeth, then along the line to the join.
SEEN_INITIAL = f"{teeth(100, 64, 28, from_top=True)} {on_the_line(26)}"
# medial ـسـ: arrives on the line, three teeth up and down, on to the left join.
SEEN_MEDIAL = f"M136 97 L128 97 {teeth(110, 74, 38, from_top=False)} {on_the_line(36)}"
# final ـس: arrives on the line, three teeth up and down, then the bowl.
SEEN_FINAL = f"M248 97 L240 97 {teeth(222, 186, 150, from_top=False)} {bowl(148)}"

LETTERS = (
    isolated("س", 232, SEEN),
    initial("س", 122, SEEN_INITIAL),
    medial("س", 136, SEEN_MEDIAL),
    final("س", 248, SEEN_FINAL),
    isolated("ش", 232, SEEN, dots=three(176, 38)),
    initial("ش", 122, SEEN_INITIAL, dots=three(64, 38)),
    medial("ش", 136, SEEN_MEDIAL, dots=three(74, 38)),
    final("ش", 248, SEEN_FINAL, dots=three(186, 38)),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "س": (
        "ثلاث أسنان صغيرة: الأولى من أعلاها إلى السطر، والثانية والثالثة صعودًا ونزولًا، ثم بطن "
        "مستديرة تحت السطر ونصعد إلى اليسار."
    ),
    "ش": ("مثل السين، ثم ثلاث نقاط فوق الأسنان: اثنتان من اليمين إلى اليسار، ثم الثالثة فوقهما."),
}
