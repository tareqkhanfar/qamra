"""Build «Qamra Display»: Baloo Bhaijaan 2 (SIL OFL 1.1, no Reserved Font Name), its hamza reading as «ء».

At 9–12 pt, and on pale name plates, Baloo's hamza over and under a letter (the mark `hamzaabove.ar`, which
أ ؤ ئ, لأ and the hamza+vowel marks are built from, and `hamzabelow.ar` under إ) is a short slanted stroke
that reads as a fatha. Here both marks are redrawn as the font's own lone hamza «ء» (`hamza.ar`, a clear
head and tail), scaled to a little more than the old mark's height and placed where it was. Nothing else
changes. The OFL asks a modified version to carry a different name: the font is «Qamra Display»; its
license and the original copyright notice are kept (OFL-QamraDisplay.txt).

    uv run python scripts/build_display_font.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FONTS = Path(__file__).resolve().parents[1] / "packages/pdf/src/qamra_pdf/fonts"
WEIGHTS = {"Medium": "BalooBhaijaan2-Medium.ttf", "ExtraBold": "BalooBhaijaan2-ExtraBold.ttf"}
FAMILY = "Qamra Display"
HEIGHT = 1.4  # the new hamza's height, as a share of the old mark's


def redraw(font: TTFont, mark: str, *, above: bool) -> float:
    glyf = font["glyf"]
    gs = font.getGlyphSet()
    old = glyf[mark]
    old.recalcBounds(glyf)
    hamza = glyf["hamza.ar"]
    hamza.recalcBounds(glyf)
    s = (old.yMax - old.yMin) * HEIGHT / (hamza.yMax - hamza.yMin)
    cx = (old.xMin + old.xMax) / 2 - (hamza.xMin + hamza.xMax) / 2 * s
    # above a letter the hamza keeps the old mark's foot; under one, its top
    dy = old.yMin - hamza.yMin * s if above else old.yMax - hamza.yMax * s
    rec = DecomposingRecordingPen(gs)
    gs["hamza.ar"].draw(rec)
    pen = TTGlyphPen(gs)
    rec.replay(TransformPen(pen, (s, 0, 0, s, cx, dy)))
    glyf[mark] = pen.glyph()
    glyf[mark].recalcBounds(glyf)
    width, _ = font["hmtx"][mark]
    font["hmtx"][mark] = (width, glyf[mark].xMin)
    return glyf[mark].yMax - old.yMax if above else glyf[mark].yMin - old.yMin


def make_room(font: TTFont, mark: str, delta: float, *, above: bool) -> None:
    """A vowel over the new, taller hamza (or under the deeper one) moves by `delta`: in the composite
    hamza+vowel glyphs, and at the anchors where a vowel attaches to a letter built with the hamza and to
    the hamza mark itself."""
    glyf = font["glyf"]
    holders = {mark}
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite() and any(c.glyphName == mark for c in g.components):
            holders.add(name)
            for c in g.components:
                if c.glyphName != mark and (c.y >= 0 if above else c.y <= 0):
                    g_c = glyf[c.glyphName]
                    g_c.recalcBounds(glyf)
                    if (g_c.yMin > 300) if above else (g_c.yMax < 100):  # a vowel, not the letter's body
                        c.y += round(delta)
    moved = lambda a: a is not None and ((a.YCoordinate > 400) if above else (a.YCoordinate < 0))  # noqa: E731
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for st in lookup.SubTable:
            kind = type(st).__name__
            if kind == "MarkBasePos":
                for name, rec in zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord, strict=True):
                    if name in holders:
                        for a in rec.BaseAnchor:
                            if moved(a):
                                a.YCoordinate += round(delta)
            elif kind == "MarkLigPos":
                ligatures = st.LigatureArray.LigatureAttach
                for name, rec in zip(st.LigatureCoverage.glyphs, ligatures, strict=True):
                    if name in holders:
                        for comp in rec.ComponentRecord:
                            for a in comp.LigatureAnchor:
                                if moved(a):
                                    a.YCoordinate += round(delta)
            elif kind == "MarkMarkPos":
                for name, rec in zip(st.Mark2Coverage.glyphs, st.Mark2Array.Mark2Record, strict=True):
                    if name == mark:
                        for a in rec.Mark2Anchor:
                            if a is not None:
                                a.YCoordinate += round(delta)


def rename(font: TTFont, weight: str) -> None:
    names = {1: FAMILY if weight == "Medium" else f"{FAMILY} {weight}", 2: "Regular", 4: f"{FAMILY} {weight}"}
    names |= {6: f"QamraDisplay-{weight}", 16: FAMILY, 17: weight}
    table = font["name"]
    for rec in list(table.names):
        if rec.nameID in (1, 3, 4, 6, 16, 17, 21, 22):
            table.removeNames(nameID=rec.nameID)
    for nid, value in names.items():
        table.setName(value, nid, 3, 1, 0x409)
        table.setName(value, nid, 1, 0, 0)
    table.setName(f"{FAMILY} {weight}; modified from Baloo Bhaijaan 2 by Qamra", 3, 3, 1, 0x409)
    old = table.getDebugName(5) or ""
    table.setName(f"{old}; Qamra: the hamza marks redrawn", 5, 3, 1, 0x409)


def main() -> None:
    for weight, source in WEIGHTS.items():
        font = TTFont(FONTS / source)
        for mark, above in (("hamzaabove.ar", True), ("hamzabelow.ar", False)):
            make_room(font, mark, redraw(font, mark, above=above), above=above)
        rename(font, weight)
        out = FONTS / f"QamraDisplay-{weight}.ttf"
        font.save(out)
        print("wrote", out)
    shutil.copyfile(FONTS / "OFL-BalooBhaijaan2.txt", FONTS / "OFL-QamraDisplay.txt")


if __name__ == "__main__":
    main()
