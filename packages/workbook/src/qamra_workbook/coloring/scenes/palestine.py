"""«أُلَوِّنُ فِلَسْطينَ»: the scenes (see `scenes.registry`), in the order of `content/coloring/palestine.yaml`.

Each scene draws a 186 × 232 mm page back to front: sky, far hills, near ground, the main subject large in the
middle, then a few friendly details in front. The frame clips everything, so backgrounds run past the edges.
"""

from __future__ import annotations

from qamra_workbook.coloring.ink import (
    EARTH,
    GRASS,
    GREEN,
    HILL,
    HILL_FAR,
    MAIN,
    ORANGE,
    PINK,
    RED,
    SKY,
    STONE,
    STONE_DEEP,
    TEAL,
    WOOD,
    WOOD_DARK,
    YELLOW,
    Pen,
    c,
    p,
    place,
    rect,
)
from qamra_workbook.coloring.parts import common as cm
from qamra_workbook.coloring.parts import heritage as hz
from qamra_workbook.coloring.parts import palestine as pl
from qamra_workbook.coloring.scenes.registry import scene


def _sky(
    pen: Pen,
    *,
    sun: tuple[float, float] | None = (158, 28),
    clouds: tuple[tuple[float, float, float], ...] = (),
) -> str:
    """The sky behind a scene (one area past the frame's edges: no outline shows), a sun, clouds."""
    out = pen.shape(rect(-6, -6, 200, 250), fill=SKY)
    if sun:
        out += place(pen, cm.sun, sun[0], sun[1], 1.0)
    for x, y, s in clouds:
        out += place(pen, cm.cloud, x, y, s)
    return out


@scene("palestine", "olive-harvest")
def olive_harvest(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(164, 24), clouds=((30, 24, 1.0),))
    out += cm.hills(pen, w, 118, 10, 3, fill=HILL_FAR, seed=4)
    out += cm.ground(pen, w, 158, fill=HILL)
    out += place(pen, pl.cloth, 92, 196, 1.0, w=176, depth=30, olives=7)
    out += place(pen, pl.olive_tree, 72, 184, 1.02)
    out += place(pen, pl.ladder, 168, 214, 1.0, rotate=-14, h=118)
    out += place(pen, cm.man, 157.5, 180.5, 0.5, flip=True, keffiyeh=True, pose="reach", beard=True)
    out += place(pen, cm.woman, 28, 226, 0.56, pose="down")
    out += place(pen, pl.basket, 60, 228, 0.62)
    out += place(pen, cm.child, 108, 228, 0.66, girl=True, pose="wave", pattern=True)
    out += place(pen, pl.basket, 136, 230, 0.5, handle=False)
    out += place(pen, cm.tuft, 176, 232, 1.0)
    return out


@scene("palestine", "olive-tree")
def olive_tree(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=None, clouds=((150, 22, 0.9),))
    out += cm.hills(pen, w, 150, 8, 3, fill=HILL_FAR, seed=8)
    out += cm.ground(pen, w, 182, fill=HILL)
    out += place(pen, pl.stone_wall, -6, 196, 1.0, w=70, h=24, rows=2, seed=3)
    out += place(pen, pl.stone_wall, 130, 196, 1.0, w=70, h=24, rows=2, seed=5)
    out += place(pen, pl.olive_tree, 93, 214, 1.12, trunk=1.45, olives=14)
    out += place(pen, cm.poppy, 24, 230, 1.0)
    out += place(pen, cm.poppy, 166, 228, 0.9)
    out += place(pen, cm.tuft, 46, 226, 1.0)
    out += place(pen, cm.tuft, 142, 228, 1.0)
    out += place(pen, cm.bird_v, 30, 26, 1.2)
    out += place(pen, cm.bird_v, 50, 18, 1.0)
    return out


@scene("palestine", "zeit-zaatar")
def zeit_zaatar(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, 175), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, -5, -5, w + 5, 170, course=22, seed=3)
    # the window: sky, a hill and an olive tree outside
    wx, wy, ww, wh = 58, 104, 70, 86
    out += pen.shape(p(pl._arch_d(wx - 5, wy, ww + 10, wh + 5)), fill=STONE_DEEP)
    out += pen.shape(p(pl._arch_d(wx, wy, ww, wh)), fill=SKY)
    out += pen.shape(
        p(f"M{wx} {wy - 22} Q{wx + 30} {wy - 40} {wx + ww} {wy - 26} L{wx + ww} {wy} L{wx} {wy} Z"), fill=HILL
    )
    out += place(pen, pl.olive_tree, wx + 46, wy - 14, 0.3, olives=0)
    out += pen.shape(rect(wx - 9, wy - 2, ww + 18, 7, 2), fill=STONE_DEEP)
    out += place(pen, cm.child, 93, 192, 0.95, girl=True, pose="wave", hair="ponytail", dress=pl.TATREEZ_RED)
    # the table
    out += pen.shape(rect(-5, 160, w + 10, 22, 0), fill=pl.WOOD_LIGHT)
    out += pen.shape(rect(-5, 178, w + 10, 60), fill=pl.CLOTH)
    cloth_band = hz.band_of(pen, w=w + 8, h=24, unit="diamonds", cell=4.8)
    out += f'<g transform="translate(-4 196)">{cloth_band}</g>'
    out += place(pen, pl.jar, 24, 174, 1.0)
    out += place(pen, pl.plate, 64, 171, 1.0, w=50)
    out += place(pen, pl.flatbread, 64, 166, 0.9)
    out += place(pen, pl.flatbread, 62, 160, 0.9)
    out += place(pen, pl.bowl, 104, 178, 1.0, w=40, contents="oil")
    out += place(pen, pl.bowl, 146, 178, 1.0, w=40, contents="zaatar")
    out += place(pen, pl.teapot, 165, 158, 0.9)
    return out


@scene("palestine", "zaatar")
def zaatar(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(30, 28), clouds=((146, 28, 1.0),))
    out += cm.hills(pen, w, 86, 12, 3, fill=HILL_FAR, seed=2)
    out += cm.ground(pen, w, 112, fill=HILL)
    out += place(pen, pl.stone_wall, -4, 120, 0.8, w=240, h=24, rows=2, seed=9)
    out += place(pen, pl.zaatar_plant, 74, 228, 1.75)
    out += place(pen, cm.child, 162, 216, 0.86, girl=False, pose="down", shirt=TEAL)
    out += place(pen, pl.basket, 126, 234, 0.72, contents="zaatar")
    out += place(pen, pl.butterfly, 150, 76, 0.9, wing=YELLOW)
    out += place(pen, cm.tuft, 14, 228, 1.0)
    return out


@scene("palestine", "taboon")
def taboon(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(160, 26), clouds=((40, 26, 0.9),))
    out += cm.hills(pen, w, 110, 10, 3, fill=HILL_FAR, seed=6)
    out += place(pen, pl.olive_tree, 150, 150, 0.55, olives=6)
    out += cm.ground(pen, w, 148, fill=EARTH)
    out += place(pen, pl.smoke, 62, 98, 1.0, h=34)
    out += place(pen, pl.taboon, 62, 190, 1.2)
    out += place(pen, cm.woman, 146, 214, 0.62, pose="hold", dress=pl.THOB)
    out += place(pen, pl.peel, 140, 167, 1.0, flip=True, length=56)
    out += place(pen, pl.flatbread, 104, 166, 0.55)
    out += place(pen, pl.basket, 56, 226, 0.9, contents="bread", handle=False)
    out += place(pen, cm.child, 104, 228, 0.6, girl=True, pose="hold", dress=PINK)
    out += place(pen, pl.flatbread, 104, 200, 0.42)
    return out


@scene("palestine", "village-house")
def village_house(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(160, 26), clouds=((36, 28, 1.0),))
    out += cm.hills(pen, w, 108, 10, 3, fill=HILL_FAR, seed=12)
    out += place(pen, pl.olive_tree, 168, 158, 0.5, olives=0)
    out += cm.ground(pen, w, 168, fill=HILL)
    out += place(pen, pl.stone_house, 86, 190, 1.3, door=-0.2, windows=(0.25,), dome=True)
    out += place(pen, pl.flower_pot, 34, 200, 1.1)
    out += place(pen, pl.flower_pot, 84, 198, 1.0, bloom=PINK)
    out += pen.shape(p("M48 192 Q60 210 52 240 L86 240 Q74 210 72 192 Z"), fill=STONE)
    out += place(pen, pl.well, 24, 232, 0.72)
    out += place(pen, pl.cat, 160, 228, 0.6)
    out += place(pen, cm.tuft, 110, 222, 1.0)
    out += place(pen, cm.poppy, 130, 232, 0.8)
    return out


@scene("palestine", "shepherd")
def shepherd(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(156, 28), clouds=((40, 30, 1.0),))
    out += cm.hills(pen, w, 104, 12, 3, fill=HILL_FAR, seed=5)
    out += place(pen, pl.olive_tree, 150, 128, 0.36, olives=0)
    out += cm.hills(pen, w, 140, 8, 2, fill=HILL, seed=3)
    out += place(pen, pl.sheep, 120, 160, 0.62, grazing=True)
    out += place(pen, pl.sheep, 160, 176, 0.7)
    out += place(pen, pl.crook, 62, 218, 0.58, h=170)
    out += place(pen, cm.man, 44, 218, 0.62, keffiyeh=True, beard=True, pose="reach", robe="#D9CBB0")
    out += place(pen, pl.sheep, 104, 212, 0.95)
    out += place(pen, pl.dog, 170, 234, 0.7, flip=True)
    out += place(pen, pl.sheep, 30, 238, 0.7, lamb=True)
    out += place(pen, cm.tuft, 86, 230, 1.0)
    return out


@scene("palestine", "sheep-lamb")
def sheep_lamb(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(30, 30), clouds=((140, 28, 1.1),))
    out += cm.hills(pen, w, 96, 10, 3, fill=HILL_FAR, seed=7)
    out += cm.ground(pen, w, 120, fill=HILL)
    out += place(pen, pl.stone_wall, -4, 128, 0.75, w=260, h=24, rows=2, seed=2)
    out += place(pen, pl.sheep, 78, 200, 1.75)
    out += place(pen, pl.sheep, 120, 228, 1.1, lamb=True, flip=True)
    out += place(pen, pl.daisy, 20, 230, 1.0)
    out += place(pen, cm.poppy, 172, 214, 0.9)
    out += place(pen, pl.daisy, 166, 236, 0.8)
    out += place(pen, pl.butterfly, 146, 84, 0.8, wing=PINK)
    return out


@scene("palestine", "grapes-figs")
def grapes_figs(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=None, clouds=((156, 70, 0.9),))
    out += cm.hills(pen, w, 150, 8, 3, fill=HILL_FAR, seed=13)
    out += cm.ground(pen, w, 180, fill=HILL)
    # the trellis: a beam across the top with the vine's leaves above it and big bunches hanging below
    out += pen.shape(rect(-6, 30, 200, 8, 2.5), fill=WOOD)
    for x, y, t, k in (
        (-2, 32, -20, 1.1),
        (40, 32, 15, 1.15),
        (82, 32, -10, 1.1),
        (124, 32, 20, 1.05),
        (166, 32, -15, 1.1),
    ):
        out += pen.shape(p(pl.grape_leaf_d(x, y, k, t)), fill=pl.LEAF_DARK)
    for x, y, t, k in ((-6, 38, 165, 0.9), (60, 38, 195, 0.85), (146, 38, 170, 0.9)):
        out += pen.shape(p(pl.grape_leaf_d(x, y, k, t)), fill=pl.VINE)
    for x, y, fill in ((26, 40, pl.GRAPE), (100, 42, pl.GRAPE_GREEN), (176, 40, pl.GRAPE)):
        out += pl.grape_bunch(pen, x=x, y=y, r=6.4, rows=5, hang=True, fill=fill)
    out += place(pen, pl.fig_branch, 196, 112, 1.15, length=96)
    out += place(pen, cm.child, 62, 214, 1.0, girl=True, pose="up", hair="bob", dress=pl.TATREEZ_RED)
    out += place(pen, pl.basket, 128, 224, 1.0, contents="figs")
    out += place(pen, pl.basket, 168, 234, 0.72, contents="grapes", handle=False)
    out += place(pen, pl.fig_half, 18, 222, 1.0)
    return out


@scene("palestine", "kites")
def kites(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=None, clouds=((166, 96, 0.8), (88, 118, 0.7)))
    out += cm.hills(pen, w, 150, 12, 3, fill=HILL_FAR, seed=21)
    out += place(pen, pl.olive_tree, 96, 170, 0.4, olives=0)
    out += cm.ground(pen, w, 176, fill=HILL)
    # each child's raised hand holds the end of a kite string (the wave pose's hand: 21 right, 84 up)
    hand = 21 * 0.82
    out += pen.stroke(p("M30 157 Q46 120 46 82"), p("M156 159 Q138 110 128 54"))
    out += place(pen, pl.kite, 46, 44, 1.2, tail=36)
    out += place(pen, pl.kite, 128, 22, 1.0, colors=(pl.SHUTTER, YELLOW, RED, GRASS), tail=40)
    out += place(pen, cm.child, 30 + hand, 226, 0.82, girl=False, pose="wave", flip=True, shirt=ORANGE)
    out += place(pen, cm.child, 156 - hand, 228, 0.82, girl=True, pose="wave", hair="pigtails", dress=PINK)
    out += place(pen, cm.bird_v, 88, 50, 1.1)
    out += place(pen, cm.bird_v, 102, 60, 0.9)
    out += place(pen, cm.poppy, 96, 232, 0.8)
    out += place(pen, cm.tuft, 176, 232, 1.0)
    return out


@scene("palestine", "grandma-story")
def grandma_story(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, h + 10), fill=SKY)
    out += cm.hills(pen, w, 120, 8, 3, fill=HILL_FAR, seed=17)
    out += cm.ground(pen, w, 150, fill=HILL)
    out += place(pen, pl.arbor, 93, 160, 1.5, bunches=4)
    out += place(pen, pl.mat, 93, 200, 1.0, w=190, depth=48, pattern=False)
    out += place(pen, pl.seated, 93, 190, 1.0, kind="grandma", hands="tell", dress=pl.THOB)
    out += place(pen, pl.seated, 32, 222, 1.0, kind="girl", hands="clap", dress=PINK)
    out += place(pen, pl.seated, 154, 222, 1.0, kind="boy", hands="lap", shirt=ORANGE)
    out += place(pen, pl.tray, 93, 222, 1.0, w=40)
    out += place(pen, pl.teapot, 87, 222, 0.5)
    out += place(pen, pl.tea_glass, 104, 221, 0.75)
    return out


@scene("palestine", "jaffa-sea")
def jaffa_sea(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(30, 30), clouds=((96, 24, 0.9),))
    # the old city on its hill, back to front
    out += pen.shape(
        pl.base_blob([(70, 160), (96, 120), (128, 96), (164, 86), (200, 92), (200, 160)]), fill=STONE
    )
    out += place(pen, pl.minaret, 170, 98, 0.62)
    out += place(pen, pl.block, 146, 104, 1.0, w=30, h=22, windows=1, dome=True)
    out += place(pen, pl.block, 186, 104, 1.0, w=26, h=24, windows=1)
    out += place(pen, pl.clock_tower, 122, 128, 0.72)
    out += place(pen, pl.block, 154, 130, 1.0, w=34, h=28, windows=2)
    out += place(pen, pl.block, 186, 128, 1.0, w=30, h=26, windows=1, dome=True)
    out += place(pen, pl.block, 100, 148, 1.0, w=30, h=22, windows=1)
    out += place(pen, pl.palm, 84, 150, 0.55)
    out += place(pen, pl.block, 134, 152, 1.0, w=36, h=24, windows=2, dome=True)
    out += place(pen, pl.block, 172, 152, 1.0, w=36, h=24, windows=2)
    out += pl.sea(pen, w, 150, rows=4, floor=240)
    out += place(pen, pl.boat, 148, 176, 0.48, hull=RED)
    out += place(pen, pl.boat, 66, 214, 1.08)
    out += place(pen, pl.gull, 50, 76, 1.0)
    out += place(pen, pl.gull, 80, 60, 0.8)
    out += place(pen, pl.gull, 26, 102, 0.7)
    return out


@scene("palestine", "jaffa-oranges")
def jaffa_oranges(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(160, 26), clouds=((40, 24, 0.9),))
    out += cm.hills(pen, w, 120, 10, 3, fill=HILL_FAR, seed=31)
    out += place(pen, pl.orange_tree, 160, 150, 0.55)
    out += cm.ground(pen, w, 160, fill=HILL)
    out += place(pen, pl.orange_tree, 70, 196, 1.2)
    out += place(pen, pl.crate, 146, 230, 1.15)
    out += place(pen, cm.child, 100, 228, 0.78, girl=False, pose="hold", shirt=pl.SHUTTER)
    out += pen.shape(c(100, 186, 6.5), fill=pl.ORANGE_FRUIT)
    out += place(pen, pl.basket, 30, 230, 0.8, contents="oranges")
    return out


@scene("palestine", "old-city-alley")
def old_city_alley(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, 120), fill=SKY)
    out += place(pen, cm.cloud, 96, 22, 0.8)
    # far away above the back wall: a dome and a minaret
    out += place(pen, pl.minaret, 116, 70, 0.6)
    out += pen.shape(p("M60 70 C60 44 96 44 96 70 Z"), fill=pl.DOME_GOLD)
    # the back wall with its arch, then the steps climbing toward it
    out += pen.shape(rect(30, 66, 126, 92), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, 30, 66, 156, 158, course=18, seed=5)
    out += pen.shape(p(pl._arch_d(66, 158, 54, 70)), fill=STONE)
    out += pen.shape(p(pl._arch_d(72, 158, 42, 62)), fill=SKY)
    steps = 6
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        y0, y1 = 150 + 88 * t0, 150 + 88 * t1
        half0, half1 = 44 + 56 * t0, 44 + 56 * t1
        out += pen.shape(
            p(f"M{93 - half0} {y0} L{93 + half0} {y0} L{93 + half1} {y1} L{93 - half1} {y1} Z"),
            fill=STONE if i % 2 else pl.LIMESTONE,
        )
    # the two houses on either side
    out += pen.shape(rect(-5, -5, 50, 245), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, -5, -5, 45, 240, course=20, seed=8)
    out += pl.arched_door(pen, 18, 236, dw=28, dh=62)
    out += pl.arched_window(pen, 20, 112, ww=20, wh=30)
    out += place(pen, pl.flower_pot, 20, 112, 1.0)
    out += pen.shape(rect(141, -5, 50, 245), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, 141, -5, 191, 240, course=20, seed=9)
    out += pl.arched_window(pen, 168, 150, ww=22, wh=34, fill=GREEN)
    out += place(pen, pl.flower_pot, 166, 236, 1.3, bloom=PINK)
    # a rope across the alley with lanterns
    out += pen.stroke(p("M45 38 Q93 58 141 38"))
    out += place(pen, pl.lantern, 70, 50, 0.9)
    out += place(pen, pl.lantern, 116, 50, 0.9)
    out += place(pen, pl.cat, 104, 210, 0.62)
    out += place(pen, pl.flower_pot, 66, 196, 0.9, bloom=RED)
    return out


@scene("palestine", "aqsa")
def aqsa(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=None, clouds=((30, 26, 0.9), (160, 34, 0.8)))
    out += place(pen, cm.bird_v, 150, 60, 1.0)
    out += place(pen, cm.bird_v, 164, 70, 0.8)
    out += cm.hills(pen, w, 150, 6, 3, fill=HILL_FAR, seed=41)
    out += place(pen, pl.qibli_mosque, 28, 172, 0.66)
    out += place(pen, pl.cypress_tree, 66, 172, 0.7)
    out += place(pen, pl.dome_of_the_rock, 110, 172, 0.84)
    out += place(pen, pl.cypress_tree, 176, 174, 0.85)
    out += place(pen, pl.cypress_tree, 6, 176, 0.6)
    # the stone platform and its steps, the grass, the old city wall in front
    out += pen.shape(rect(-5, 170, w + 10, 12), fill=STONE_DEEP)
    out += cm.ground(pen, w, 182, fill=HILL)
    out += place(pen, pl.olive_tree, 30, 204, 0.34, olives=0)
    out += place(pen, pl.olive_tree, 156, 204, 0.34, olives=0)
    out += place(pen, pl.city_wall, -6, 240, 1.0, w=200, h=30, merlons=8)
    return out


@scene("palestine", "souk")
def souk(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, 180), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, -5, -5, w + 5, 175, course=22, seed=12)
    out += pen.shape(p(pl._arch_d(56, 120, 74, 84)), fill=STONE_DEEP)
    out += pen.shape(p(pl._arch_d(62, 120, 62, 76)), fill="#8F6A45")
    out += place(pen, cm.man, 93, 208, 0.74, pose="wave", robe=pl.SHUTTER)
    out += place(pen, pl.awning, -5, 18, 1.0, w=w + 10, h=26, stripes=7)
    out += place(pen, pl.lantern, 30, 46, 1.0)
    out += place(pen, pl.lantern, 156, 46, 1.0)
    # the counter with fruit, sacks of spice in front
    out += pen.shape(rect(-5, 156, w + 10, 10, 2), fill=WOOD)
    out += pen.shape(rect(0, 164, w, 80), fill=pl.WOOD_LIGHT)
    out += pen.stroke(p(f"M0 196 L{w} 196"))
    out += place(pen, pl.fruit_pile, 34, 157, 1.0, r=7, base=4)
    out += place(pen, pl.fruit_pile, 150, 157, 1.0, r=7, base=4, fill=RED)
    out += place(pen, pl.sack, 26, 238, 1.05, spice=pl.SPICE_RED)
    out += place(pen, pl.sack, 70, 240, 1.0, spice=pl.SPICE_YELLOW, scoop=True)
    out += place(pen, pl.sack, 114, 238, 1.05, spice=pl.SPICE_GREEN)
    out += place(pen, pl.sack, 160, 240, 1.0, spice=pl.SPICE_BROWN)
    return out


@scene("palestine", "maqluba")
def maqluba(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, 180), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, -5, -5, w + 5, 175, course=24, seed=21)
    out += place(pen, pl.lantern, 34, 0, 1.0)
    out += place(pen, pl.lantern, 152, 0, 1.0)
    # the family behind the table: the big flip!
    out += place(pen, cm.child, 28, 202, 0.86, girl=True, pose="up", hair="pigtails", dress=PINK)
    out += place(pen, cm.child, 158, 202, 0.86, girl=False, pose="wave", flip=True, shirt=ORANGE)
    out += place(pen, cm.man, 93, 212, 0.75, pose="up", beard=True, robe=pl.SHUTTER)
    out += place(pen, pl.pot, 93, 98, 1.0, w=56)
    # the table with its cloth, and the maqluba turned out on its tray
    out += pen.shape(rect(-5, 170, w + 10, 16), fill=pl.WOOD_LIGHT)
    out += pen.shape(rect(-5, 184, w + 10, 60), fill=pl.CLOTH)
    out += (
        f'<g transform="translate(-4 206)">{hz.band_of(pen.at(1), w=w + 8, h=22, unit="teeth", cell=4.6)}</g>'
    )
    out += place(pen, pl.maqluba, 93, 190, 0.9)
    out += place(pen, pl.bowl, 22, 190, 0.85, contents="labneh")
    out += place(pen, pl.plate, 164, 186, 1.0, w=40)
    return out


@scene("palestine", "knafeh")
def knafeh(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, 140), fill=pl.LIMESTONE)
    out += pl.stone_courses(pen, -5, -5, w + 5, 135, course=24, seed=4)
    out += pl.arched_window(pen, 93, 70, ww=34, wh=52, fill=SKY)
    out += place(pen, pl.lantern, 30, 0, 1.1)
    out += place(pen, pl.lantern, 156, 0, 1.1)
    out += place(pen, cm.child, 46, 160, 0.95, girl=True, pose="wave", hair="bob", dress=pl.TATREEZ_RED)
    out += place(pen, cm.child, 140, 160, 0.95, girl=False, pose="wave", flip=True, shirt=TEAL)
    out += pen.shape(rect(-5, 130, w + 10, 110), fill=pl.WOOD_LIGHT)
    out += pen.stroke(p(f"M-5 142 L{w + 5} 142"))
    out += place(pen, pl.knafeh_tray, 93, 182, 1.12, w=140)
    out += place(pen, pl.knafeh_slice, 38, 226, 1.0, w=40)
    out += place(pen, pl.tea_glass, 148, 230, 1.1)
    out += place(pen, pl.teapot, 172, 234, 0.8)
    return out


@scene("palestine", "tatreez-dress")
def tatreez_dress(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, h + 10), fill=pl.LIMESTONE)
    # a peg and a wooden hanger
    out += pen.shape(c(93, 12, 4), fill=WOOD_DARK)
    out += pen.stroke(p("M93 14 L93 22"), weight=MAIN)
    out += pen.shape(pl.band([(42, 30), (93, 22), (144, 30)], 5), fill=WOOD)
    out += place(pen, pl.thob, 93, 228, 1.02)
    return out


@scene("palestine", "tatreez-pattern")
def tatreez_pattern(pen: Pen, w: float, h: float) -> str:
    cell = 6.4
    out = pen.shape(rect(-5, -5, w + 10, h + 10), fill=hz.LINEN)
    # a frame of stepped teeth all round
    band_h = 26
    teeth = hz.band_of(pen, w=w + 8, h=band_h, unit="teeth", cell=cell)
    out += f'<g transform="translate(-4 4)">{teeth}</g>'
    out += f'<g transform="translate({w + 4} {h - 4}) rotate(180)">{teeth}</g>'
    # the medallion: a big star, four cypress trees, four small stars in the corners
    cx, cy = w / 2, h / 2
    out += place(
        pen,
        hz.motif,
        cx,
        cy,
        1.0,
        layers=[
            (hz.star8(5, 8), hz.TATREEZ_RED),
            (hz.star8(3, 5), hz.TATREEZ_GOLD),
            (hz.star8(1, 2), hz.TATREEZ_GREEN),
        ],
        cell=cell,
    )
    for dx, dy, turn in ((0, -1, 0), (0, 1, 180), (-1, 0, -90), (1, 0, 90)):
        x = cx + dx * cell * 11.5
        y = cy + dy * cell * 11.5
        tree = hz.motif(pen, layers=[(hz.shift(hz.cypress(7), 0, 3), hz.TATREEZ_GREEN)], cell=cell * 0.9)
        out += f'<g transform="translate({x:.2f} {y:.2f}) rotate({turn})">{tree}</g>'
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        out += place(
            pen,
            hz.motif,
            cx + dx * cell * 9.8,
            cy + dy * cell * 11.6,
            1.0,
            layers=[(hz.diamond(3), hz.TATREEZ_NAVY), (hz.diamond(1), hz.TATREEZ_GOLD)],
            cell=cell,
        )
    return out


@scene("palestine", "keffiyeh")
def keffiyeh(pen: Pen, w: float, h: float) -> str:
    out = pen.shape(rect(-5, -5, w + 10, h + 10), fill=pl.CLOTH)
    out += place(pen, hz.keffiyeh, w / 2, h / 2, 1.0, size=172, step=21)
    return out


@scene("palestine", "wildflowers")
def wildflowers(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(158, 28), clouds=((40, 30, 1.0),))
    out += cm.hills(pen, w, 104, 10, 3, fill=HILL_FAR, seed=51)
    out += cm.ground(pen, w, 128, fill=HILL)
    # far flowers, then the big ones in front
    out += place(pen, cm.poppy, 20, 150, 0.7)
    out += place(pen, pl.daisy, 64, 146, 0.6)
    out += place(pen, pl.anemone, 112, 148, 0.5)
    out += place(pen, cm.poppy, 166, 152, 0.7)
    out += place(pen, pl.anemone, 42, 236, 1.9, lean=-0.06)
    out += place(pen, pl.daisy, 96, 232, 1.9, lean=0.05)
    out += place(pen, cm.poppy, 146, 236, 2.3)
    out += place(pen, pl.daisy, 180, 236, 1.1, lean=0.1)
    out += place(pen, pl.butterfly, 120, 70, 1.0)
    out += place(pen, pl.butterfly, 62, 92, 0.7, wing=PINK, spots=pl.SHUTTER)
    return out


@scene("palestine", "sunbird")
def sunbird(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(156, 30), clouds=((30, 26, 0.9),))
    out += cm.hills(pen, w, 190, 10, 3, fill=HILL_FAR, seed=61)
    out += cm.ground(pen, w, 214, fill=HILL)
    # a flowering branch across the page; the bird perched on it reaches for a flower
    twigs = [
        pl.band([(-8, 196), (40, 182), (100, 178), (150, 166), (196, 150)], 8),
        pl.band([(40, 182), (30, 150), (34, 118)], 5),
        pl.band([(150, 166), (156, 130), (150, 98)], 5),
    ]
    out += pen.shape(*twigs, fill=pl.BARK)
    leaves = [
        p(cm.leaf_d(x, y, 28, 11, a))
        for x, y, a in (
            (20, 188, 150),
            (32, 150, -150),
            (34, 134, -40),
            (126, 172, 80),
            (154, 128, -30),
            (152, 112, -150),
            (178, 158, -60),
        )
    ]
    out += pen.shape(*leaves, fill=GRASS)
    flowers = [
        p(pl.trumpet_flower(x, y, 32, a))
        for x, y, a in ((34, 118, -100), (34, 118, -40), (150, 98, -80), (150, 98, -135), (196, 150, -70))
    ]
    out += pen.shape(*flowers, fill=RED)
    out += place(pen, pl.sunbird, 96, 175, 1.3)
    out += place(pen, cm.tuft, 20, 230, 1.0)
    out += place(pen, cm.tuft, 166, 230, 1.0)
    return out


@scene("palestine", "cactus")
def cactus(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(30, 28), clouds=((150, 30, 1.0),))
    out += cm.hills(pen, w, 116, 10, 3, fill=HILL_FAR, seed=71)
    out += place(pen, pl.stone_house, 150, 136, 0.4, door=0.0, windows=(), dome=True)
    out += cm.ground(pen, w, 140, fill=EARTH)
    out += place(pen, pl.stone_wall, -6, 186, 1.0, w=210, h=40, rows=3, seed=7)
    out += place(pen, pl.cactus, 96, 222, 1.3)
    out += place(pen, cm.stone, 24, 232, 1.4)
    out += place(pen, cm.tuft, 168, 230, 1.2)
    out += place(pen, pl.hen, 160, 232, 0.9)
    return out


@scene("palestine", "almond-terraces")
def almond_terraces(pen: Pen, w: float, h: float) -> str:
    out = _sky(pen, sun=(160, 26), clouds=((44, 26, 0.9),))
    # three terraces stepping down the hill, each held by a dry-stone wall
    out += pen.shape(p(f"M-6 92 Q90 74 {w + 6} 86 L{w + 6} 240 L-6 240 Z"), fill=HILL_FAR)
    out += place(pen, pl.olive_tree, 40, 100, 0.3, olives=0)
    out += place(pen, pl.olive_tree, 146, 102, 0.3, olives=0)
    out += place(pen, pl.stone_wall, -6, 116, 0.6, w=330, h=24, rows=2, seed=3)
    out += pen.shape(rect(-6, 116, w + 12, 50), fill=HILL)
    out += place(pen, pl.olive_tree, 150, 152, 0.36, olives=0)
    out += place(pen, pl.stone_wall, -6, 170, 0.8, w=250, h=26, rows=2, seed=6)
    out += pen.shape(rect(-6, 170, w + 12, 80), fill=GRASS)
    out += place(pen, pl.almond_tree, 66, 222, 1.25)
    out += place(pen, cm.child, 150, 224, 0.72, girl=True, pose="wave", dress=pl.ALMOND, hair="ponytail")
    out += place(pen, pl.butterfly, 154, 132, 0.6, wing=PINK, spots=YELLOW)
    out += place(pen, pl.daisy, 112, 232, 0.9)
    out += place(pen, cm.poppy, 20, 234, 0.8)
    return out
