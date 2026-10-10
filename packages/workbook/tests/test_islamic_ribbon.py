"""The unit's ribbon at the top of every page of «قلبي يعرف الله»: well-formed SVG (its motif used to pass
through Markup.replace, which escaped the strip's opening tag into the text «&lt;svg …» and left a stray
</svg>), and a motif that sits whole inside the trim (it used to straddle the cut: the trim sliced the top off
every star on every page)."""

import re
import xml.dom.minidom

import pytest
from qamra_workbook.pictures.islamic import MOTIFS, ribbon_svg
from qamra_workbook.render.islamic_units import UNITS
from qamra_workbook.render.pages.islamic_common import RIBBON_H
from qamra_workbook.render.spec import Geometry

G = Geometry(trim_w=210.0, trim_h=280.0)


@pytest.mark.parametrize("motif", sorted(MOTIFS))
def test_the_ribbon_is_well_formed_svg_for_every_motif(motif: str) -> None:
    svg = str(ribbon_svg(motif, "#5B6FC0", "#FFFFFF", G.page_w, RIBBON_H, G.bleed))
    xml.dom.minidom.parseString(svg)  # raises on a stray or unbalanced tag
    assert "&lt;" not in svg and "&#34;" not in svg
    assert svg.count("<svg") == 1 == svg.count("</svg>")


def test_every_units_motif_has_a_drawing() -> None:
    assert {u.motif for u in UNITS.values()} <= set(MOTIFS)


def test_the_ribbon_runs_into_the_bleed_and_its_motif_sits_inside_the_trim() -> None:
    svg = str(ribbon_svg("stars", "#5B6FC0", "#FFFFFF", G.page_w, RIBBON_H, G.bleed))
    view = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    assert view and float(view.group(1)) == G.page_w and float(view.group(2)) == RIBBON_H + G.bleed
    band = re.search(r'<rect x="0" y="0" width="[\d.]+" height="([\d.]+)"', svg)
    assert band and float(band.group(1)) > G.bleed + 4  # a solid band below the cut, not only scallops
    motif = re.search(r'<g transform="translate\(4 ([\d.]+)\)"', svg)
    assert motif and float(motif.group(1)) >= G.bleed  # the motif's top is below the trim line
