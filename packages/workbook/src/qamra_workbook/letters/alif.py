"""ا and the لا ligature: they never join the next letter, so they have isolated and final forms only.

The final alif and the alif of لا go up from the line: the pen arrives from the previous letter (or from
the lam) and climbs without lifting.
"""

from __future__ import annotations

from qamra_workbook.letters.hand import final, isolated

# isolated ا: straight down from the top line to the base line.
ALIF = "M26 -25 L26 97"
# final ـا: arrives on the line, turns up and climbs to the top line.
ALIF_FINAL = "M56 97 L40 97 C32 97 28 93 28 85 L28 -25"
# isolated لا: the lam down to the line, round the narrow bottom to the left, then the alif up, leaning
# out to the left.
LAM_ALIF = "M84 -25 L84 72 C84 88 76 97 64 97 C56 97 50 94 47 86 L14 -22"
# final ـلا: arrives on the line, up the lam and back down, then the same bottom and alif.
LAM_ALIF_FINAL = (
    "M116 97 L100 97 C94 97 91 94 90 88 L88 -25 L85 72 C84 88 77 97 66 97 C58 97 52 94 49 86 L16 -22"
)

LETTERS = (
    isolated("ا", 52, ALIF),
    final("ا", 56, ALIF_FINAL),
    isolated("لا", 100, LAM_ALIF),
    final("لا", 116, LAM_ALIF_FINAL),
)


# How each letter is written, in words, for the educator's review sheet.
HOW = {
    "ا": (
        "من السطر العلوي ننزل بخط مستقيم إلى السطر. في آخر الكلمة يصل القلم من الحرف السابق ويصعد إلى الأعلى."
    ),
    "لا": (
        "اللام من السطر العلوي إلى السطر، ندور قليلًا إلى اليسار، ثم نصعد بالألف مائلة إلى الأعلى "
        "دون أن نرفع القلم."
    ),
}
