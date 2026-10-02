"""Code-drawn ornaments for the redesigned pages (Addendum 11 §3, §5): vector, print-sharp, no fonts.

They are the finished fallbacks for the optional decor images (E1–E5): a moon portrait frame, tatreez and
moon borders, corner flourishes, scattered stars, crayon doodles, a peeking moon creature, small icons and the
star badge for page numbers. Every function returns inline SVG markup in millimetre units.
"""

import math
import random

from markupsafe import Markup

GOLD = "#E9A92B"
GOLD_DEEP = "#B97A12"
GOLD_LIGHT = "#FFE7A6"


def _svg(view: str, body: str, cls: str = "", style: str = "") -> Markup:
    return Markup(  # nosec B704 (numbers and fixed shapes only)
        f'<svg class="{cls}" viewBox="{view}" style="{style}" aria-hidden="true">{body}</svg>'
    )


def _pt(x: float, y: float) -> str:
    return f"{x:.2f} {y:.2f}"


def star_path(cx: float, cy: float, r: float, points: int = 5, inner: float = 0.45, rot: float = -90) -> str:
    pts = []
    for i in range(points * 2):
        rad = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 180 / points)
        pts.append(_pt(cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return "M " + " L ".join(pts) + " Z"


def sparkle_path(cx: float, cy: float, r: float) -> str:
    k = r * 0.16
    return (
        f"M {_pt(cx, cy - r)} C {_pt(cx + k, cy - k)} {_pt(cx + k, cy - k)} {_pt(cx + r, cy)} "
        f"C {_pt(cx + k, cy + k)} {_pt(cx + k, cy + k)} {_pt(cx, cy + r)} "
        f"C {_pt(cx - k, cy + k)} {_pt(cx - k, cy + k)} {_pt(cx - r, cy)} "
        f"C {_pt(cx - k, cy - k)} {_pt(cx - k, cy - k)} {_pt(cx, cy - r)} Z"
    )


def crescent_path(
    cx: float, cy: float, r: float, cut: float = 0.78, dx: float = 0.32, dy: float = -0.22
) -> str:
    """A crescent: the disc (cx, cy, r) minus a disc of radius cut·r shifted by (dx, dy)·r."""
    r2 = r * cut
    ox, oy = cx + dx * r, cy + dy * r
    d = math.hypot(ox - cx, oy - cy)
    a = (r * r - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, r * r - a * a))
    ux, uy = (ox - cx) / d, (oy - cy) / d
    px, py = cx + a * ux, cy + a * uy
    p1 = (px + h * uy, py - h * ux)
    p2 = (px - h * uy, py + h * ux)
    return f"M {_pt(*p1)} A {r:.2f} {r:.2f} 0 1 0 {_pt(*p2)} A {r2:.2f} {r2:.2f} 0 1 1 {_pt(*p1)} Z"


def star_badge(number: str, fill: str, ring: str, ink: str) -> Markup:
    """The page number in an eight-point star (rub el hizb shape) — the text is set in HTML on top."""
    s = 12
    sq = (
        f'<rect x="2.2" y="2.2" width="7.6" height="7.6" rx=".7" fill="{fill}" stroke="{ring}" '
        'stroke-width=".45"/>'
    )
    body = (
        sq
        + f'<g transform="rotate(45 6 6)">{sq}</g>'
        + f'<rect x="2.65" y="2.65" width="6.7" height="6.7" rx=".5" fill="{fill}"/>'
        + f'<g transform="rotate(45 6 6)"><rect x="2.65" y="2.65" width="6.7" height="6.7" rx=".5" '
        f'fill="{fill}"/></g>'
    )
    return _svg(f"0 0 {s} {s}", body, "badge-star")


def moon_frame(gold: str = GOLD, deep: str = GOLD_DEEP, light: str = GOLD_LIGHT) -> Markup:
    """An ornate moon frame around a round portrait (the portrait sits in the 64 % hole, centered)."""
    c = 50.0
    grad = (
        f'<defs><linearGradient id="mf-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light}"/>'
        f'<stop offset=".5" stop-color="{gold}"/><stop offset="1" '
        f'stop-color="{deep}"/></linearGradient></defs>'
    )
    crescent = f'<path d="{crescent_path(c - 1, c + 1, 47, cut=0.86, dx=0.16, dy=-0.13)}" fill="url(#mf-g)"/>'
    rings = (
        f'<circle cx="{c}" cy="{c}" r="34.6" fill="none" stroke="url(#mf-g)" stroke-width="2.6"/>'
        f'<circle cx="{c}" cy="{c}" r="37.4" fill="none" stroke="{gold}" stroke-width=".5" '
        'stroke-dasharray=".1 2.2" '
        f'stroke-linecap="round"/>'
    )
    beads = "".join(
        f'<path d="M {_pt(c + 34.6 * math.cos(math.radians(a)), c + 34.6 * math.sin(math.radians(a)) - 1.5)} '
        f'l 1.5 1.5 l -1.5 1.5 l -1.5 -1.5 Z" fill="{light}" stroke="{deep}" stroke-width=".35"/>'
        for a in range(-60, 121, 30)
    )
    hangers = ""
    for x, length, r in ((70, 14, 3.4), (80, 8, 2.6), (60, 19, 2.2)):
        y0 = c - math.sqrt(max(0.0, 47**2 - (x - c + 1) ** 2)) + 3
        hangers += (
            f'<line x1="{x}" y1="{y0:.1f}" x2="{x}" y2="{y0 - length:.1f}" stroke="{gold}" '
            'stroke-width=".45"/>'
            f'<path d="{star_path(x, y0 - length - r * 0.6, r)}" fill="url(#mf-g)" stroke="{deep}" '
            'stroke-width=".3"/>'
        )
    sparkles = "".join(
        f'<path d="{sparkle_path(x, y, r)}" fill="{gold}"/>'
        for x, y, r in ((12, 18, 3.2), (90, 86, 2.6), (8, 70, 2))
    )
    return _svg("-4 -14 108 118", grad + crescent + rings + beads + hangers + sparkles, "moon-frame")


def corner_flourish(color: str = GOLD, accent: str = "#C8343C") -> Markup:
    """One page-corner ornament (top-left as drawn; CSS mirrors it for the other corners)."""
    body = (
        f'<path d="M 2 34 C 2 16 16 2 34 2" fill="none" stroke="{color}" stroke-width="1.1" '
        'stroke-linecap="round"/>'
        f'<path d="M 7 34 C 7 20 20 7 34 7" fill="none" stroke="{color}" stroke-width=".5" '
        'stroke-linecap="round"/>'
        f'<path d="M 2 34 C 1 40 5 44 10 44" fill="none" stroke="{color}" stroke-width=".8" '
        'stroke-linecap="round"/>'
        f'<path d="M 34 2 C 40 1 44 5 44 10" fill="none" stroke="{color}" stroke-width=".8" '
        'stroke-linecap="round"/>'
        f'<path d="{star_path(13, 13, 5.2, 8, 0.55, -90)}" fill="{color}"/>'
        f'<circle cx="13" cy="13" r="1.4" fill="{accent}"/>'
        f'<path d="M 22 15 l 1.6 1.6 l -1.6 1.6 l -1.6 -1.6 Z" fill="{accent}"/>'
        f'<path d="M 15 22 l 1.6 1.6 l -1.6 1.6 l -1.6 -1.6 Z" fill="{accent}"/>'
        f'<circle cx="44" cy="11.5" r="1.1" fill="{color}"/><circle cx="11.5" cy="44" r="1.1" '
        f'fill="{color}"/>'
    )
    return _svg("0 0 48 48", body, "corner")


def tatreez_frame(w: float, h: float, band: float, red: str, green: str, gold: str = GOLD) -> Markup:
    """A rectangular cross-stitch border (w × h mm, band mm wide) around a picture window."""
    cell = band / 3
    pat = (
        f'<pattern id="tz" width="{band * 2:.3f}" height="{band:.3f}" patternUnits="userSpaceOnUse">'
        f'<rect width="{band * 2:.3f}" height="{band:.3f}" fill="#FFF8EC"/>'
    )

    # an eight-point star of stitches, then a small diamond: Palestinian tatreez motifs, simplified
    def stitch(x: float, y: float, color: str) -> str:
        k = cell * 0.42
        return (
            f'<path d="M {_pt(x - k, y - k)} L {_pt(x + k, y + k)} M {_pt(x + k, y - k)} L '
            f'{_pt(x - k, y + k)}" '
            f'stroke="{color}" stroke-width="{cell * 0.28:.3f}" stroke-linecap="round"/>'
        )

    cx, cy = band / 2, band / 2
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        pat += stitch(cx + dx * cell, cy + dy * cell, red)
    for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
        pat += stitch(cx + dx * cell, cy + dy * cell, green)
    pat += stitch(band * 1.5, band / 2, red)
    pat += "</pattern>"
    b = band
    frame_path = f"M 0 0 H {w} V {h} H 0 Z M {b} {b} V {h - b} H {w - b} V {b} Z"
    body = (
        f"<defs>{pat}</defs>"
        f'<path d="{frame_path}" fill="url(#tz)" fill-rule="evenodd"/>'
        f'<rect x=".35" y=".35" width="{w - 0.7}" height="{h - 0.7}" fill="none" stroke="{gold}" '
        'stroke-width=".7"/>'
        f'<rect x="{b - 0.35}" y="{b - 0.35}" width="{w - 2 * b + 0.7}" height="{h - 2 * b + 0.7}" '
        'fill="none" '
        f'stroke="{gold}" stroke-width=".7"/>'
    )
    for x, y in ((0, 0), (w, 0), (0, h), (w, h)):
        body += (
            f'<rect x="{x - b * 0.62:.2f}" y="{y - b * 0.62:.2f}" width="{b * 1.24:.2f}" '
            f'height="{b * 1.24:.2f}" '
            f'fill="{red}" transform="rotate(45 {x} {y})"/>'
            f'<path d="{star_path(x, y, b * 0.48, 8, 0.6, -90)}" fill="{gold}"/>'
        )
    return _svg(f"0 0 {w} {h}", body, "tatreez-frame", "overflow:visible")


def moon_border(w: float, h: float, band: float, ink: str, gold: str = GOLD) -> Markup:
    """A night border: deep band with small crescents and stars (for night-glow books)."""
    body = (
        f'<path d="M 0 0 H {w} V {h} H 0 Z M {band} {band} V {h - band} H {w - band} V {band} Z" '
        f'fill="{ink}" fill-rule="evenodd"/>'
        f'<rect x="{band - 0.5}" y="{band - 0.5}" width="{w - 2 * band + 1}" height="{h - 2 * band + 1}" '
        f'fill="none" stroke="{gold}" stroke-width=".8"/>'
    )
    step = band * 2.2
    i = 0
    x = band
    while x < w - band:
        for y in (band / 2, h - band / 2):
            if i % 3 == 0:
                body += f'<path d="{crescent_path(x, y, band * 0.3, 0.8, 0.35, -0.2)}" fill="{gold}"/>'
            else:
                body += f'<path d="{star_path(x, y, band * 0.22)}" fill="{GOLD_LIGHT}"/>'
        x += step
        i += 1
    y = band + step / 2
    while y < h - band:
        for x2 in (band / 2, w - band / 2):
            body += f'<path d="{star_path(x2, y, band * 0.2)}" fill="{GOLD_LIGHT}"/>'
        y += step
    return _svg(f"0 0 {w} {h}", body, "moon-border", "overflow:visible")


def scattered_stars(
    w: float,
    h: float,
    n: int,
    seed: int,
    color: str = GOLD,
    keep_out: tuple[float, float, float, float] | None = None,
) -> Markup:
    """Small stars and sparkles spread over a w × h mm area (deterministic), avoiding `keep_out`."""
    rnd = random.Random(seed)
    body, placed, tries = "", 0, 0
    while placed < n and tries < n * 30:
        tries += 1
        x, y = rnd.uniform(4, w - 4), rnd.uniform(4, h - 4)
        if keep_out and keep_out[0] < x < keep_out[2] and keep_out[1] < y < keep_out[3]:
            continue
        r = rnd.uniform(1.0, 2.6)
        op = rnd.uniform(0.45, 0.95)
        shape = sparkle_path(x, y, r * 1.3) if placed % 3 == 0 else star_path(x, y, r)
        body += f'<path d="{shape}" fill="{color}" opacity="{op:.2f}"/>'
        placed += 1
    return _svg(f"0 0 {w} {h}", body, "stars-layer")


CRAYONS = ("#E8453C", "#F28C28", "#F6C431", "#4CAF50", "#2F80ED", "#9B51E0", "#EC4899")


def crayon_doodles(
    w: float, h: float, frame: tuple[float, float, float, float], seed: int = 7, top_band: float = 0.0
) -> Markup:
    """Children's crayon doodles around a drawing frame (x0, y0, x1, y1 in mm): stars, hearts, a sun, a
    swirl, zigzags, a flower and a rainbow, with a waxy double stroke. Nothing lands inside the frame or in
    the middle of the top band (the page title)."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = frame

    def crayon(d: str, color: str, width: float = 1.3) -> str:
        jitter = f'transform="translate({rnd.uniform(-0.35, 0.35):.2f} {rnd.uniform(-0.35, 0.35):.2f})"'
        return (
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity=".92"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width * 0.55:.2f}" '
            'stroke-linecap="round" '
            f'stroke-linejoin="round" opacity=".55" {jitter}/>'
        )

    def heart(cx: float, cy: float, s: float) -> str:
        return (
            f"M {_pt(cx, cy + s * 0.9)} C {_pt(cx - s * 1.4, cy - s * 0.1)} "
            f"{_pt(cx - s * 0.6, cy - s * 1.2)} "
            f"{_pt(cx, cy - s * 0.35)} C {_pt(cx + s * 0.6, cy - s * 1.2)} {_pt(cx + s * 1.4, cy - s * 0.1)} "
            f"{_pt(cx, cy + s * 0.9)} Z"
        )

    def sun(cx: float, cy: float, r: float) -> str:
        rays = " ".join(
            f"M {_pt(cx + r * 1.35 * math.cos(a), cy + r * 1.35 * math.sin(a))} "
            f"L {_pt(cx + r * 1.85 * math.cos(a), cy + r * 1.85 * math.sin(a))}"
            for a in (math.radians(k * 45) for k in range(8))
        )
        return f"M {_pt(cx + r, cy)} A {r} {r} 0 1 1 {_pt(cx + r - 0.01, cy - 0.2)} {rays}"

    def swirl(cx: float, cy: float, r: float) -> str:
        pts = []
        for i in range(48):
            t = i / 47 * 3.2 * math.pi
            rr = r * (0.15 + 0.85 * i / 47)
            pts.append(_pt(cx + rr * math.cos(t), cy + rr * math.sin(t)))
        return "M " + " L ".join(pts)

    def zigzag(x: float, y: float, length: float, amp: float) -> str:
        n = 7
        return "M " + " L ".join(_pt(x + length * i / n, y + (amp if i % 2 else -amp)) for i in range(n + 1))

    def flower(cx: float, cy: float, r: float) -> str:
        petals = " ".join(
            f"M {_pt(cx, cy)} C {_pt(cx + r * math.cos(a - 0.5), cy + r * math.sin(a - 0.5))} "
            f"{_pt(cx + r * math.cos(a + 0.5), cy + r * math.sin(a + 0.5))} {_pt(cx, cy)}"
            for a in (math.radians(k * 72) for k in range(5))
        )
        return petals + f" M {_pt(cx, cy + r * 0.2)} L {_pt(cx, cy + r * 2.2)}"

    def rainbow(cx: float, cy: float, r: float) -> list[tuple[str, str]]:
        return [
            (f"M {_pt(cx - rr, cy)} A {rr} {rr} 0 0 1 {_pt(cx + rr, cy)}", c)
            for rr, c in (
                (r, CRAYONS[0]),
                (r * 0.8, CRAYONS[2]),
                (r * 0.6, CRAYONS[3]),
                (r * 0.4, CRAYONS[4]),
            )
        ]

    def spot() -> tuple[float, float]:
        """A point in the margin band around the frame."""
        for _ in range(60):
            x, y = rnd.uniform(6, w - 6), rnd.uniform(6, h - 6)
            inside = x0 - 7 < x < x1 + 7 and y0 - 7 < y < y1 + 7
            under_title = y < top_band and w * 0.18 < x < w * 0.82
            if not inside and not under_title:
                return x, y
        return 8.0, 8.0

    body = ""
    shapes = [
        "star",
        "heart",
        "sun",
        "swirl",
        "zigzag",
        "flower",
        "star",
        "heart",
        "rainbow",
        "star",
        "swirl",
    ]
    for i, shape in enumerate(shapes):
        color = CRAYONS[i % len(CRAYONS)]
        x, y = spot()
        if shape == "star":
            body += crayon(star_path(x, y, rnd.uniform(4, 6)), color)
        elif shape == "heart":
            body += crayon(heart(x, y, rnd.uniform(3.2, 4.4)), color)
        elif shape == "sun":
            body += crayon(sun(x, y, 3.6), CRAYONS[2])
        elif shape == "swirl":
            body += crayon(swirl(x, y, 4.5), color)
        elif shape == "zigzag":
            body += crayon(zigzag(x - 8, y, 16, 2.2), color)
        elif shape == "flower":
            body += crayon(flower(x, y, 4.2), color)
        elif shape == "rainbow":
            for d, c in rainbow(x, y + 3, 7):
                body += crayon(d, c, 1.5)
    return _svg(f"0 0 {w} {h}", body, "doodles")


def wavy_frame(w: float, h: float, color: str, fill: str = "#FFFDF8", wave: float = 2.4) -> Markup:
    """A playful scalloped frame (w × h mm) for the drawing page."""

    def edge(xa: float, ya: float, xb: float, yb: float, n: int) -> str:
        out = ""
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            mx, my = xa + (xb - xa) * (t0 + t1) / 2, ya + (yb - ya) * (t0 + t1) / 2
            nx, ny = (yb - ya), -(xb - xa)
            norm = math.hypot(nx, ny) or 1
            cx, cy = mx + nx / norm * wave * -1, my + ny / norm * wave * -1
            ex, ey = xa + (xb - xa) * t1, ya + (yb - ya) * t1
            out += f" Q {_pt(cx, cy)} {_pt(ex, ey)}"
        return out

    m = wave + 1
    d = f"M {m} {m}" + edge(m, m, w - m, m, 16) + edge(w - m, m, w - m, h - m, 13)
    d += edge(w - m, h - m, m, h - m, 16) + edge(m, h - m, m, m, 13) + " Z"
    body = (
        f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="1.2" stroke-linejoin="round"/>'
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width=".5" stroke-dasharray="1.6 2.2" '
        f'transform="translate({w * 0.03:.2f} {h * 0.03:.2f}) scale(.94)" opacity=".7"/>'
    )
    return _svg(f"0 0 {w} {h}", body, "wavy-frame")


def peek_creature(body_color: str = "#F6C14E", ink: str = "#16204A") -> Markup:
    """Qamra's little moon creature peeking over an edge, both hands on it (fallback companion)."""
    body = (
        f'<path d="{crescent_path(30, 30, 24, 0.82, 0.3, -0.25)}" fill="{body_color}"/>'
        f'<circle cx="23" cy="24" r="9" fill="{body_color}"/>'
        f'<ellipse cx="20" cy="22" rx="2.4" ry="3" fill="#FFFFFF"/><ellipse cx="27.5" cy="22" rx="2.4" '
        'ry="3" fill="#FFFFFF"/>'
        f'<circle cx="20.6" cy="22.8" r="1.4" fill="{ink}"/><circle cx="28" cy="22.8" r="1.4" fill="{ink}"/>'
        f'<path d="M 21 28 Q 24 30.5 27 28" fill="none" stroke="{ink}" stroke-width=".9" '
        'stroke-linecap="round"/>'
        f'<circle cx="16.5" cy="27" r="1.6" fill="#F28C8C" opacity=".6"/><circle cx="31" cy="27" r="1.6" '
        'fill="#F28C8C" opacity=".6"/>'
        f'<ellipse cx="13" cy="44" rx="4.2" ry="3" fill="{body_color}" stroke="#D99A1F" stroke-width=".5"/>'
        f'<ellipse cx="36" cy="44" rx="4.2" ry="3" fill="{body_color}" stroke="#D99A1F" stroke-width=".5"/>'
        f'<path d="{sparkle_path(46, 8, 3.4)}" fill="{body_color}"/>'
    )
    return _svg("0 0 54 48", body, "peek-creature")


def icon(name: str, color: str, bg: str) -> Markup:
    """Small round card icons for the parents page."""
    shapes = {
        "seed": (
            f'<path d="M 12 19 V 11" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="M 12 12 C 12 7 8 5 5 6 C 5 10 8 12 12 12 Z" fill="{color}"/>'
            f'<path d="M 12 10 C 12 6 15 4 19 5 C 19 9 16 10.5 12 10 Z" fill="{color}" opacity=".75"/>'
        ),
        "talk": (
            f'<path d="M 4 6 h 11 a 2 2 0 0 1 2 2 v 5 a 2 2 0 0 1 -2 2 h -6 l -3 3 v -3 h -2 a 2 2 0 0 1 -2 '
            f'-2 v -5 a 2 2 0 0 1 2 -2 Z" fill="{color}"/>'
            f'<path d="M 19 10 h 1 a 2 2 0 0 1 2 2 v 4 a 2 2 0 0 1 -2 2 h -1 v 2.5 l -2.6 -2.5 h -3 a 2 2 0 '
            f'0 1 -1.6 -.8" fill="none" stroke="{color}" stroke-width="1.3" stroke-linejoin="round"/>'
        ),
        "heart": (
            f'<path d="M 12 19 C 4 13 4 7 8 6 C 10 5.5 11.5 7 12 8 C 12.5 7 14 5.5 16 6 C 20 7 20 13 12 19 '
            f'Z" fill="{color}"/>'
        ),
    }
    return _svg("0 0 24 24", f'<circle cx="12" cy="12" r="12" fill="{bg}"/>' + shapes[name], "icon")


def tape(color: str, pattern: str = "dots") -> Markup:
    """A strip of washi tape (34 × 10 mm) with torn ends."""
    edge_l = "M 0 0 L 1.2 1.6 L 0 3.3 L 1.1 5 L 0 6.7 L 1.2 8.4 L 0 10"
    edge_r = "L 34 10 L 32.8 8.4 L 34 6.7 L 32.9 5 L 34 3.3 L 32.8 1.6 L 34 0 Z"
    deco = ""
    if pattern == "dots":
        deco = "".join(
            f'<circle cx="{x}" cy="{y}" r=".7" fill="#FFFFFF" opacity=".75"/>'
            for x in range(4, 32, 4)
            for y in (3, 7)
        )
    elif pattern == "stripes":
        deco = "".join(
            f'<path d="M {x} 0 L {x - 4} 10" stroke="#FFFFFF" stroke-width="1" opacity=".55"/>'
            for x in range(5, 38, 4)
        )
    else:  # moons
        deco = "".join(
            f'<path d="{crescent_path(x, 5, 1.8, 0.8, 0.35, -0.2)}" fill="#FFFFFF" opacity=".8"/>'
            for x in range(5, 32, 6)
        )
    body = f'<path d="{edge_l} {edge_r}" fill="{color}" opacity=".88"/>{deco}'
    return _svg("0 0 34 10", body, "tape")
