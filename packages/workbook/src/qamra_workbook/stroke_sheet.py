"""The educator's review sheet for the Arabic letter strokes (decisions of 28 Sept 2026, item 3): A4, RTL, one
page per letter with every form large on the writing lines, green numbered start dots, direction arrows,
the order of strokes, marks and dots, sample joins and a sign-off box. A first page explains how to review;
the last one collects the final signature. Nothing is printed for sale before she signs the letter shapes.

    uv run python -m qamra_workbook.stroke_sheet [--out DIR] [--only ب,ت]

Writes arabic-strokes.pdf and png/NN-<letter>.png page previews to out/letters/.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from pathlib import Path

import pypdfium2 as pdfium
from markupsafe import escape

from qamra_pdf import html_to_pdf
from qamra_workbook.geometry import Point, Stroke, bounds
from qamra_workbook.letters import ALPHABET, ARABIC, EXPECTED, HOW, NAMES, placed, word
from qamra_workbook.letters.hand import BASE, LOW, MID, TOP
from qamra_workbook.letters.model import Letter
from qamra_workbook.render import marks

FONTS = Path(__file__).parents[3] / "pdf" / "src" / "qamra_pdf" / "fonts"
OUT = Path("out/letters")

NAVY = "#16204A"
TRACK = "#F9DA8F"  # the letter's body, as wide as a child's tracing
LINE = "#4A5078"  # the path itself, dotted like the tracing pages
ARROW = "#E27D63"
START = "#2FA36B"  # start dots are green ("go")
DOT = "#7B5EA7"  # the letter's dots, numbered after the strokes
GUIDE = "#9BB7E0"
BASE_LINE = "#E27D63"

VIEW_TOP, VIEW_BOTTOM = TOP - 17, LOW + 13  # the same band on every drawing, so sizes compare
PAD = 16  # letter units left and right of the box
TRACK_W, LINE_W = 15.0, 2.2
ARROW_EVERY, ARROW_SIZE = 40.0, 10.5
START_R, DOT_SHOWN_R = 10.5, 9.5

FORM_NAMES = {
    "isolated": "منفصل",
    "initial": "في أول الكلمة",
    "medial": "في وسط الكلمة",
    "final": "في آخر الكلمة",
}


def digits(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def num(x: float) -> str:
    text = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def el(tag: str, content: str = "", /, **attrs: float | str) -> str:
    """An SVG element; `stroke_width` becomes `stroke-width`, `class_` becomes `class`."""
    parts = " ".join(
        f'{k.rstrip("_").replace("_", "-")}="{num(v) if isinstance(v, int | float) else escape(v)}"'
        for k, v in attrs.items()
    )
    return f"<{tag} {parts}>{content}</{tag}>" if content else f"<{tag} {parts}/>"


def line_path(d: str, color: str, width: float, **attrs: float | str) -> str:
    return el(
        "path",
        d=d,
        fill="none",
        stroke=color,
        stroke_width=width,
        stroke_linecap="round",
        stroke_linejoin="round",
        **attrs,
    )


def arrow_head(point: Point, angle: float, size: float = ARROW_SIZE) -> str:
    s = size
    head = [(s * 0.62, 0.0), (-s * 0.5, -s * 0.56), (-s * 0.22, 0.0), (-s * 0.5, s * 0.56)]
    d = "M" + " L".join(f"{num(x)} {num(y)}" for x, y in head) + " Z"
    turn = f"translate({num(point[0])} {num(point[1])}) rotate({num(angle)})"
    return el("path", d=d, fill=ARROW, stroke="#FFFFFF", stroke_width=s * 0.14, transform=turn)


def arrows(stroke: Stroke, every: float = ARROW_EVERY) -> list[str]:
    """Arrowheads along a stroke, clear of its start dot and its end. Where the pen comes back along the
    same line (a tooth or a stem in the middle of a word), each arrow moves to the right-hand side of its
    own direction, so the way up and the way down show side by side."""
    length = stroke.length
    if length < START_R * 2.6:
        return []
    first, last = START_R + ARROW_SIZE * 0.9, length - ARROW_SIZE * 0.4
    count = max(1, math.floor((last - first) / every) + 1)
    step = (last - first) / count
    out = []
    for k in range(count):
        s = first + step * (k + 0.5) if count > 1 else (first + last) / 2
        point, angle = stroke.at(s / length)
        if comes_back(stroke, s, point, angle):
            a = math.radians(angle)
            point = (point[0] - math.sin(a) * 7.5, point[1] + math.cos(a) * 7.5)
        out.append(arrow_head(point, angle))
    return out


def comes_back(stroke: Stroke, s: float, point: Point, angle: float) -> bool:
    """Whether another part of the stroke passes close to `point` going the other way."""
    for c, q in zip(stroke.lengths, stroke.polyline, strict=True):
        if abs(c - s) > 34 and math.dist(point, q) < 11:
            other = stroke.at(c / stroke.length)[1]
            if abs((other - angle + 180) % 360 - 180) > 100:
                return True
    return False


def badge(point: Point, label: str, color: str, r: float) -> str:
    x, y = point
    size = r * 1.25
    return el("circle", cx=x, cy=y, r=r, fill=color, stroke="#FFFFFF", stroke_width=r * 0.2) + el(
        "text", escape(label), x=x, y=y + size * 0.36, font_size=size, class_="badge"
    )


def guides(x0: float, x1: float) -> str:
    """The writing lines: top (ascenders), dashed tooth line, the red base line and the dotted tail line."""

    def across(y: float, color: str, width: float, dash: str = "none") -> str:
        return line_path(f"M{num(x0)} {num(y)} L{num(x1)} {num(y)}", color, width, stroke_dasharray=dash)

    return (
        across(TOP, GUIDE, 1.3)
        + across(MID, GUIDE, 1.2, "7 6")
        + across(BASE, BASE_LINE, 2.2)
        + across(LOW, GUIDE, 1.2, "2 5")
    )


def track(shape: Letter) -> str:
    """The letter's body as a wide soft track with the dotted path on top, and its dots. A small mark (the
    little hamza of ك) gets a narrower track, so its head stays an open curl."""
    widths = [TRACK_W * 0.5 if m else TRACK_W for m in shape.marks]
    out = [line_path(s.d, TRACK, w) for s, w in zip(shape.strokes, widths, strict=True)]
    out += [line_path(s.d, LINE, LINE_W, stroke_dasharray="0.1 5.2") for s in shape.strokes]
    out += [el("circle", cx=x, cy=y, r=shape.dot_r, fill=DOT, opacity=0.35) for x, y in shape.dots]
    return "".join(out)


def order(shape: Letter, first: int = 1) -> str:
    """Arrows along every stroke, a green start dot numbered in writing order, then the numbered dots. A
    small mark has one arrow outside its shape and its start dot beside it, never on it (`render.marks`)."""
    obstacles = [*marks.outline(shape.strokes, TRACK_W / 2, 2.0), *((d, shape.dot_r) for d in shape.dots)]
    places = marks.badge_points(
        shape.strokes,
        shape.small,
        START_R,
        mark_radius=START_R * 0.85,
        reach=TRACK_W * 0.25,
        obstacles=obstacles,
    )
    out = []
    for s, small in zip(shape.strokes, shape.small, strict=True):
        if small:
            taken = [*obstacles, *((p, START_R) for p in places)]
            out.append(marks.side_arrow(s, ARROW_SIZE * 0.8, TRACK_W * 0.25, taken, ARROW)[0])
        else:
            out += arrows(s)
    for k, (point, small) in enumerate(zip(places, shape.small, strict=True), start=first):
        out.append(badge(point, digits(k), START, START_R * 0.85 if small else START_R))
    for k, point in enumerate(shape.dots, start=first + len(shape.strokes)):
        out.append(badge(point, digits(k), DOT, DOT_SHOWN_R))
    return "".join(out)


def join_marks(points: list[Point]) -> str:
    return "".join(
        el("circle", cx=x, cy=y, r=5.2, fill="#FFFFFF", stroke=NAVY, stroke_width=1.8) for x, y in points
    )


def svg(view_x0: float, view_x1: float, body: str, height_mm: float) -> str:
    view_h = VIEW_BOTTOM - VIEW_TOP
    width_mm = (view_x1 - view_x0) * height_mm / view_h
    view = " ".join(num(v) for v in (view_x0, VIEW_TOP, view_x1 - view_x0, view_h))
    return (
        f'<svg viewBox="{view}" width="{num(width_mm)}mm" height="{num(height_mm)}mm" '
        f'aria-hidden="true">{body}</svg>'
    )


def form_svg(shape: Letter, height_mm: float) -> str:
    """One form on its writing lines, with its join points marked."""
    x0, x1 = -PAD, shape.width + PAD
    joins = [p for p in (shape.join_right, shape.join_left) if p is not None]
    body = guides(x0, x1) + track(shape) + join_marks(joins) + order(shape)
    return svg(x0, x1, body, height_mm)


def word_svg(letters: list[Letter], height_mm: float) -> str:
    """Forms placed box to box, right to left: the pen goes on from one letter to the next at each join
    (marked), and a new green start dot shows every time it is lifted."""
    xs, total = placed(letters, gap=12)
    x0, x1 = -PAD, total + PAD
    tracks, signs, joins, number = [], [], [], 1
    for x, shape in zip(xs, letters, strict=True):
        moved = [s.scaled(1, x, 0) for s in shape.strokes]
        tracks += [
            line_path(s.d, TRACK, TRACK_W * 0.5 if m else TRACK_W)
            for s, m in zip(moved, shape.marks, strict=True)
        ]
        tracks += [line_path(s.d, LINE, LINE_W, stroke_dasharray="0.1 5.2") for s in moved]
        signs += [
            a for s, m in zip(moved, shape.small, strict=True) if not m for a in arrows(s, ARROW_EVERY * 1.6)
        ]
        places = mark_places(shape, moved)
        for k in range(len(moved)):
            if k == 0 and shape.join_right is not None:
                continue  # the pen arrives from the previous letter
            signs.append(badge(places[k], digits(number), START, START_R))
            number += 1
        tracks += [el("circle", cx=px + x, cy=py, r=shape.dot_r, fill=DOT) for px, py in shape.dots]
        if shape.join_left is not None:
            joins.append((x + shape.join_left[0], shape.join_left[1]))
    return svg(x0, x1, guides(x0, x1) + "".join(tracks) + "".join(signs) + join_marks(joins), height_mm)


def mark_places(shape: Letter, moved: list[Stroke]) -> list[Point]:
    """The start dot of each stroke of a letter in a word: on its start, a small mark's beside it."""
    obstacles = marks.outline(moved, TRACK_W / 2, 2.0)
    return marks.badge_points(
        moved, shape.small, START_R, mark_radius=START_R, reach=TRACK_W * 0.25, obstacles=obstacles
    )


CSS = """
@font-face { font-family: "Baloo Bhaijaan 2"; src: url("{fonts}/BalooBhaijaan2-ExtraBold.ttf");
  font-weight: 800; }
@font-face { font-family: "Plex"; src: url("{fonts}/IBMPlexSansArabic-Regular.ttf"); font-weight: 400; }
@font-face { font-family: "Plex"; src: url("{fonts}/IBMPlexSansArabic-SemiBold.ttf"); font-weight: 600; }
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Plex", sans-serif; color: #16204A; font-size: 10.5pt; line-height: 1.55; }
.page { width: 210mm; height: 297mm; padding: 11mm 12mm 9mm; display: flex; flex-direction: column;
  gap: 3.2mm; page-break-after: always; overflow: hidden; background: #FFFDF8; }
h1, h2 { font-family: "Baloo Bhaijaan 2", sans-serif; font-weight: 800; margin: 0; line-height: 1.2; }
header { display: flex; align-items: center; gap: 5mm; border-bottom: 1mm solid #F2B33D;
  padding-bottom: 2.5mm; }
.glyph { width: 21mm; height: 21mm; border-radius: 50%; background: #FFF1CC; display: grid;
  place-items: center; }
header h1 { font-size: 24pt; }
.kicker { color: #5B6385; font-weight: 600; font-size: 9.5pt; }
.how { font-size: 10pt; background: #F3F6FC; border-radius: 3mm; padding: 2mm 4mm; }
.forms { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
.cell:only-child { grid-column: 1 / -1; }
.cell { background: #FFFFFF; border: 0.35mm solid #EADFC8; border-radius: 3.5mm; padding: 1.5mm 2mm 1mm;
  display: flex; flex-direction: column; align-items: center; }
.cell .top { align-self: stretch; display: flex; justify-content: space-between; align-items: center; }
.cell .name { font-weight: 600; font-size: 9.5pt; background: #FFF1CC; border-radius: 2mm; padding: 0 2.5mm; }
.cell .form { font-size: 17pt; color: #5B6385; line-height: 1; }
.joins { display: flex; flex-wrap: wrap; gap: 3mm; }
.join { flex: 1; background: #FFFFFF; border: 0.35mm solid #EADFC8; border-radius: 3.5mm; padding: 1.5mm 3mm;
  display: flex; flex-direction: column; align-items: center; }
.join .label { font-weight: 600; font-size: 10pt; align-self: flex-start; }
.signoff { border: 0.5mm solid #16204A; border-radius: 3.5mm; padding: 2.5mm 4mm;
  display: grid; grid-template-columns: auto 1fr auto 1fr; gap: 1.2mm 4mm; align-items: end; }
.signoff h3 { margin: 0; font-size: 11pt; }
.signoff .choices { grid-column: 2 / -1; display: flex; gap: 8mm; }
.signoff .wide { grid-column: 2 / -1; }
.box { display: inline-block; width: 5mm; height: 5mm; border: 0.45mm solid #16204A; border-radius: 1mm;
  vertical-align: middle; margin-inline-end: 1.5mm; }
.rule { border-bottom: 0.3mm solid #9AA0B8; height: 6.5mm; }
footer { display: flex; justify-content: space-between; color: #8A90A8; font-size: 8.5pt; }
.grow { flex: 1; }
ol { margin: 0; padding-inline-start: 6mm; list-style-type: arabic-indic; }
svg text.badge { fill: #FFFFFF; font-family: "Plex", sans-serif; font-weight: 600; text-anchor: middle; }
.intro p, .intro li { margin: 0 0 1.4mm; }
.intro h2 { font-size: 15pt; margin-top: 1mm; }
.note { border-radius: 3mm; padding: 3mm 4mm; background: #FDEBE6; border: 0.4mm solid #E27D63;
  font-weight: 600; }
.legend { display: grid; grid-template-columns: auto 1fr; gap: 1.5mm 4mm; align-items: center; }
.hero { display: flex; justify-content: space-between; align-items: center; }
.final { border: 0.6mm solid #16204A; border-radius: 3.5mm; padding: 3mm 5mm 4mm; display: grid;
  grid-template-columns: auto 1fr auto 1fr auto 1fr; gap: 2mm 3mm; align-items: end; background: #FFFFFF; }
.final h3 { grid-column: 1 / -1; margin: 0 0 2mm; font-size: 12pt; }
.checklist { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2mm 4mm; }
.checklist div { border-bottom: 0.3mm solid #EADFC8; padding: 1mm 0; font-size: 11pt; }
"""


def form_label(shape: Letter) -> str:
    """How the form is usually printed on its own: بـ ـبـ ـب."""
    return {"initial": "{}ـ", "medial": "ـ{}ـ", "final": "ـ{}"}.get(shape.form, "{}").format(shape.char)


def solid(shape: Letter, size_mm: float) -> str:
    """A small solid drawing of the letter from its own strokes (for the page header)."""
    x0, _, x1, _ = bounds(list(shape.strokes))
    y0, y1 = TOP - 10, LOW + 10
    side = max(x1 - x0, y1 - y0) + 20
    cx = (x0 + x1) / 2
    body = "".join(line_path(s.d, "#16204A", 9) for s in shape.strokes) + "".join(
        el("circle", cx=x, cy=y, r=8, fill="#16204A") for x, y in shape.dots
    )
    view = " ".join(num(v) for v in (cx - side / 2, (y0 + y1) / 2 - side / 2, side, side))
    return f'<svg viewBox="{view}" width="{num(size_mm)}mm" height="{num(size_mm)}mm">{body}</svg>'


def page(body: str, number: int, total: int) -> str:
    footer = (
        f"<footer><span>مسارات الحروف العربية · قمرة</span>"
        f"<span>صفحة {digits(number)} من {digits(total)}</span></footer>"
    )
    return f'<section class="page">{body}{footer}</section>'


# Joins per letter: the letter joined to the next one, then short words it appears in.
SAMPLES: dict[str, tuple[str, ...]] = {
    "ا": ("با", "باب", "ماما"), "ب": ("با", "كتب"), "ت": ("تا", "بنت"), "ث": ("ثا", "مثلث"),
    "ج": ("جا", "نجمة"), "ح": ("حا", "بحر"), "خ": ("خا", "نخلة"), "د": ("بد", "ولد", "يد"),
    "ذ": ("بذ", "لذيذ", "ذيل"), "ر": ("بر", "شجرة", "نار"), "ز": ("بز", "خبز", "موز"), "س": ("سا", "شمس"),
    "ش": ("شا", "مشط"), "ص": ("صا", "قفص"), "ض": ("ضا", "بيض"), "ط": ("طا", "قطة"), "ظ": ("ظا", "ظل"),
    "ع": ("عا", "لعبة"), "غ": ("غا", "صمغ"), "ف": ("فا", "سيف"), "ق": ("قا", "طبق"), "ك": ("كا", "سمكة"),
    "ل": ("لب", "جمل"), "م": ("ما", "قلم"), "ن": ("نا", "لبن"), "ه": ("ها", "فهد"),
    "و": ("بو", "حوت", "ورد"), "ي": ("يا", "بيت"), "ة": ("بة", "قطة", "وردة"), "ى": ("بى", "على", "مشى"),
    "ء": ("ماء", "سماء", "بدء"), "لا": ("بلا", "سلام", "لا"),
}  # fmt: skip


def spelled(text: str) -> str:
    """«بـ + ـا» for a two-letter join; the word itself otherwise."""
    try:
        shapes = word(text)
    except KeyError:
        return text
    return " + ".join(form_label(s) for s in shapes) if len(shapes) == 2 else text


def letter_page(char: str, index: int, number: int, total: int) -> str:
    forms = [ARABIC[(char, f)] for f in EXPECTED[char]]
    size = 57 if len(forms) > 2 else 80  # four forms in a 2 × 2 grid; fewer ones larger, side by side
    cells = "".join(
        f'<div class="cell"><div class="top"><div class="name">{FORM_NAMES[s.form]}</div>'
        f'<div class="form">{escape(form_label(s))}</div></div>{form_svg(s, size)}</div>'
        for s in forms
    )
    joins = []
    for text in SAMPLES.get(char, ()):
        try:
            drawing = word_svg(word(text), 31 if len(forms) > 2 else 42)
        except KeyError:
            continue  # a letter of the sample is not drawn yet
        joins.append(f'<div class="join"><div class="label">{escape(spelled(text))}</div>{drawing}</div>')
    name = NAMES[char]
    body = (
        f'<header><div class="glyph">{solid(forms[0], 18)}</div><div>'
        f'<div class="kicker">الحرف {digits(index)} من {digits(len(ALPHABET))}</div>'
        f"<h1>{escape(name)} «{escape(char)}»</h1></div></header>"
        f'<div class="how">{escape(HOW.get(char, ""))}</div>'
        f'<div class="forms">{cells}</div>'
        f'<div class="joins">{"".join(joins)}</div><div class="grow"></div>'
        f'<div class="signoff"><h3>رأي المربّية في {escape(name)}:</h3><div class="choices">'
        '<div><span class="box"></span>موافق ✓</div><div><span class="box"></span>يحتاج تعديلًا</div></div>'
        '<div>ملاحظات:</div><div class="rule wide"></div><div></div><div class="rule wide"></div>'
        '<div>التوقيع:</div><div class="rule"></div><div>التاريخ:</div><div class="rule"></div></div>'
    )
    return page(body, number, total)


SLUGS = dict(
    zip(
        ALPHABET,
        (
            *("alif", "ba", "ta", "tha", "jeem", "hha", "kha", "dal", "thal", "ra", "zay", "seen", "sheen"),
            *("sad", "dad", "tah", "zah", "ain", "ghain", "fa", "qaf", "kaf", "lam", "meem", "noon", "ha"),
            *("waw", "ya", "ta-marbuta", "alif-maqsura", "hamza", "lam-alif"),
        ),
        strict=True,
    )
)

# The choices the educator confirms, listed on the first page.
CHOICES = (
    "الأشكال الموصولة من اليمين (في وسط الكلمة وآخرها) تبدأ من نقطة الوصل على السطر: القلم يصل من الحرف "
    "السابق دون أن يُرفع.",
    "في وسط الكلمة وآخرها نصعد إلى السنّ أو العصا ثم ننزل على الخط نفسه (سهم إلى الأعلى وسهم إلى الأسفل).",
    "الجيم والحاء والخاء: نبدأ من طرف الرأس الأيسر، نمشي قليلًا إلى اليمين، ثم ننزل وندور.",
    "العين والغين: نبدأ من أعلى الرأس يمينًا ونلفّ إلى اليسار. في وسط الكلمة وآخرها الرأس حلقة صغيرة مغلقة.",
    "الحلقات (ف ق م و ص ض ط ظ): نصعد من نقطة اتصالها على السطر وندور مع عقارب الساعة. في وسط الكلمة "
    "وآخرها يمشي القلم على السطر تحت الحلقة حتى نقطة اتصالها ثم يدور.",
    "الألف في آخر الكلمة وألف «لا»: نكتبها من السطر صعودًا، لأن القلم يصل من الحرف السابق.",
    "الطاء والظاء: الحلقة أولًا، ثم العصا من السطر العلوي.",
    "الكاف: في أول الكلمة خط واحد (الرأس المائل ثم السطر)، وفي وسطها السطر أولًا ثم الرأس، ومنفصلة وفي "
    "آخرها الهمزة الصغيرة بعد الجسم.",
    "الهاء: شكل لكل موضع (خط في الوسط منفصلة وفي الأول، حلقتان في الوسط، حلقة واحدة في الآخر).",
    "النقاط بعد الحرف كله ومن اليمين إلى اليسار، والثلاث نقطتان ثم الثالثة فوقهما. نقطتا الياء المنفصلة "
    "داخل بطنها.",
)


def legend_svg(body: str, x0: float, x1: float, y0: float, y1: float, height_mm: float) -> str:
    view = " ".join(num(v) for v in (x0, y0, x1 - x0, y1 - y0))
    width = (x1 - x0) * height_mm / (y1 - y0)
    return f'<svg viewBox="{view}" width="{num(width)}mm" height="{num(height_mm)}mm">{body}</svg>'


def legend() -> str:
    across = (
        line_path("M0 -8 L70 -8", GUIDE, 1.6)
        + line_path("M0 4 L70 4", GUIDE, 1.5, stroke_dasharray="7 6")
        + line_path("M0 16 L70 16", BASE_LINE, 2.4)
        + line_path("M0 28 L70 28", GUIDE, 1.5, stroke_dasharray="2 5")
    )
    rows = [
        (badge((12, 0), digits(1), START, START_R), "النقطة الخضراء: من هنا يبدأ الخط، ورقمها ترتيبه."),
        (line_path("M60 0 L0 0", TRACK, TRACK_W) + arrow_head((30, 0), 180), "السهم: اتجاه حركة القلم."),
        (
            badge((12, 0), digits(2), DOT, DOT_SHOWN_R),
            "النقطة البنفسجية: نقاط الحرف، ورقمها ترتيبها بعد الخطوط.",
        ),
        (join_marks([(12, 0)]), "الحلقة البيضاء: نقطة الوصل على السطر مع الحرف السابق أو التالي."),
        (
            across,
            "السطور: العلوي لطول الألف واللام والكاف والطاء، والمتقطّع لرؤوس الأسنان، والأحمر يجلس عليه "
            "الحرف، والمنقّط لأعمق ما تنزل إليه الذيول.",
        ),
    ]
    out = []
    for k, (body, text) in enumerate(rows):
        tall = k == len(rows) - 1  # the four lines need more room
        drawing = legend_svg(body, -2, 72, -14, 32 if tall else 14, 11 if tall else 7)
        out.append(f"<div>{drawing}</div><div>{text}</div>")
    return "".join(out)


def intro_page(total: int) -> str:
    choices = "".join(f"<li>{escape(c)}</li>" for c in CHOICES)
    body = (
        '<div class="intro"><div class="hero"><div>'
        "<h1 style='font-size: 24pt'>مسارات كتابة الحروف العربية</h1>"
        '<p class="kicker">ورقة مراجعة لمربّية الروضة، حرفًا حرفًا</p></div>'
        f"<div>{word_svg(word('قمرة'), 26)}</div></div>"
        "<p>رسمنا في قمرة لكل حرف عربي، بكل أشكاله (منفصلًا، وفي أول الكلمة ووسطها وآخرها)، مسارًا بخطّ واحد "
        "يتتبّعه الطفل: من أين يبدأ، وإلى أين يتّجه، وبأي ترتيب تأتي الخطوط والنقاط. رسمنا المسارات بأيدينا "
        "نقطةً نقطة ولم نأخذها من خطّ مطبعي، وستظهر الأشكال نفسها في كل صفحات التتبّع في دوسياتنا.</p>"
        f'<h2>كيف تقرئين الصفحة؟</h2><div class="legend">{legend()}</div>'
        "<h2>كيف تراجعين؟</h2><ol>"
        "<li>هل يشبه كل شكل الحرف كما تكتبينه للأطفال في الروضة؟</li>"
        "<li>هل نقطة البداية والاتجاه صحيحان؟ وهل ترتيب الخطوط والنقاط صحيح؟</li>"
        "<li>هل تتصل الحروف بسلاسة في أمثلة الوصل أسفل الصفحة؟</li>"
        "<li>ضعي ✓ عند «موافق»، أو اكتبي ما يلزم تعديله، ووقّعي أسفل كل صفحة.</li></ol>"
        f"<h2>اختيارات نحتاج رأيك فيها</h2><ol>{choices}</ol></div>"
        '<div class="grow"></div><p class="note">مهم: لن نطبع أي دوسية للبيع قبل توقيعك على أشكال الحروف. '
        "نعدّل كل ما تطلبينه ونرسل لك الصفحة من جديد حتى توافقي عليها.</p>"
    )
    return page(body, 1, total)


def closing_page(chars: list[str], number: int, total: int) -> str:
    items = "".join(f'<div><span class="box"></span>{escape(NAMES[c])} «{escape(c)}»</div>' for c in chars)
    body = (
        '<div class="intro"><h1 style="font-size: 22pt">الاعتماد النهائي</h1>'
        "<p>بعد مراجعة كل الصفحات، ضعي ✓ عند كل حرف وافقتِ عليه، ثم وقّعي أدناه.</p></div>"
        f'<div class="checklist">{items}</div>'
        '<h3 style="margin: 3mm 0 0">ملاحظات عامة</h3>'
        + '<div class="rule"></div>'
        * 6
        + '<div class="grow"></div>'
        '<div class="final"><h3>راجعتُ مسارات الحروف في هذا الملف وأوافق على اعتمادها في دوسيات قمرة.</h3>'
        '<div>الاسم:</div><div class="rule"></div><div>التوقيع:</div><div class="rule"></div>'
        '<div>التاريخ:</div><div class="rule"></div></div>'
    )
    return page(body, number, total)


def document(chars: list[str]) -> str:
    total = len(chars) + 2
    pages = [intro_page(total)]
    pages += [letter_page(c, ALPHABET.index(c) + 1, i, total) for i, c in enumerate(chars, start=2)]
    pages.append(closing_page(chars, total, total))
    css = CSS.replace("{fonts}", FONTS.as_uri())
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        f"<title>مسارات الحروف العربية</title><style>{css}</style></head><body>{''.join(pages)}</body></html>"
    )


def previews(pdf: Path, out: Path, names: list[str], dpi: int = 110) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(pdf)
    paths = []
    try:
        for i, name in enumerate(names):
            path = out / f"{i + 1:02d}-{name}.png"
            doc[i].render(scale=dpi / 72).to_pil().convert("RGB").save(path, optimize=True)
            paths.append(path)
    finally:
        doc.close()
    return paths


async def render(out: Path, chars: list[str], dpi: int = 110) -> tuple[Path, list[Path]]:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pdf = await html_to_pdf(document(chars), out / "arabic-strokes.pdf")
    for old in (out / "png").glob("*.png"):
        old.unlink()
    names = ["intro", *(SLUGS[c] for c in chars), "sign-off"]
    return pdf, previews(pdf, out / "png", names, dpi)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--only", help="comma-separated letters (for quick iterations)")
    parser.add_argument("--dpi", type=int, default=110, help="PNG preview resolution")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    chars = [c for c in ALPHABET if c in args.only.split(",")] if args.only else list(ALPHABET)
    missing = [f"{c} ({f})" for c in chars for f in EXPECTED.get(c, ("?",)) if (c, f) not in ARABIC]
    if missing:
        print("✗ no stroke data for:", ", ".join(missing))
        return 1
    pdf, pngs = asyncio.run(render(args.out, chars, args.dpi))
    print("wrote", pdf, f"({len(pngs)} pages) and", pngs[0].parent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
