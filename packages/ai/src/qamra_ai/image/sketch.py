"""Offline "sketch" image provider: draws each page from the design's illustration parts (`Scene`, `Kid`,
`Companion` in design/canvas, ported from apps/web/src/components/art) with a paper texture.

No network and $0. It reads the same prompt the real models get, so layouts, text areas, plates, outfits
and extra characters show up in the right places. Used for sample books before keys exist, demos, and
end-to-end tests of the review queue. Rendering uses Chromium (already needed for the PDFs).
"""

import hashlib
import re
from typing import Any

from playwright.async_api import Browser, Playwright, async_playwright

from qamra_ai.cost import CostEntry
from qamra_ai.image.base import TIER_PX, GeneratedImage, ImageRequest, aspect_px

INK = "#1C2140"
SKINS = ("#E8B98F", "#C98F63", "#F3CFAE", "#A8704A", "#DDAA7E")
HAIRS = ("#3A2A22", "#1C1410", "#6B4E34", "#2B1D14")
COLOR_WORDS = {
    "coral": "#E9826B",
    "red": "#E9826B",
    "sage": "#7FA38A",
    "green": "#7FA38A",
    "mint": "#9CCFB8",
    "lilac": "#A99BD6",
    "purple": "#A99BD6",
    "night-blue": "#22306A",
    "navy": "#2C3E8C",
    "light-blue": "#9DB8E8",
    "blue": "#5B6FC0",
    "yellow": "#F2B33D",
    "mustard": "#E0A43A",
    "cream": "#F3EAD8",
}
HIJAB_COLORS = {
    "cream": "#EFE3C8",
    "navy": "#2C3E8C",
    "white": "#F6F1E6",
    "lilac": "#A99BD6",
    "light-blue": "#9DB8E8",
    "sage": "#7FA38A",
}


# ---- parts ---------------------------------------------------------------------------------------


def kid_svg(
    *,
    skin: str,
    hair: str,
    outfit: str,
    hair_style: str,
    hijab: bool,
    hijab_color: str,
    pose: str,
    cap: bool,
    glasses: bool,
) -> str:
    wave = (
        f'<path d="M170 232 C192 214 202 192 204 170" fill="none" stroke="{outfit}" stroke-width="24" '
        f'stroke-linecap="round"/><circle cx="205" cy="160" r="13" fill="{skin}" stroke="{INK}" '
        f'stroke-width="2.5"/>'
        if pose == "wave"
        else ""
    )
    head: list[str] = []
    if hijab:
        head.append(
            f'<path d="M42 124 A78 82 0 0 1 198 124 L206 236 C170 256 70 256 34 236 Z" fill="{hijab_color}" stroke="{INK}" stroke-width="2.5"/>'
        )
    else:
        head.append(f'<path d="M60 126 A60 66 0 0 1 180 126 L184 152 L56 152 Z" fill="{hair}"/>')
        if hair_style == "long":
            head.append(
                f'<path d="M58 120 C50 170 54 200 70 214 L92 200 L86 130 Z M182 120 C190 170 186 200 170 214 L148 200 L154 130 Z" fill="{hair}" stroke="{INK}" stroke-width="2.5"/>'
            )
        head.append(
            f'<circle cx="68" cy="132" r="11" fill="{skin}" stroke="{INK}" stroke-width="2.5"/><circle cx="172" cy="132" r="11" fill="{skin}" stroke="{INK}" stroke-width="2.5"/>'
        )
    head.append(
        f'<ellipse cx="120" cy="128" rx="52" ry="58" fill="{skin}" stroke="{INK}" stroke-width="2.5"/>'
    )
    if hijab:
        head.append(
            f'<path d="M66 120 C66 64 174 64 174 120 C158 94 82 94 66 120 Z" fill="{hijab_color}" stroke="{INK}" stroke-width="2.5"/>'
        )
    else:
        head.append(
            f'<path d="M64 116 C68 62 172 54 178 116 C162 98 134 90 108 100 C94 106 80 112 64 116 Z" fill="{hair}" stroke="{INK}" stroke-width="2.5"/>'
        )
        if hair_style == "curly":
            head.append(
                f'<g fill="{hair}" stroke="{INK}" stroke-width="2.5"><circle cx="78" cy="88" r="16"/><circle cx="100" cy="72" r="17"/><circle cx="126" cy="68" r="17"/><circle cx="150" cy="76" r="16"/><circle cx="166" cy="96" r="14"/></g>'
            )
    head.append(
        '<path d="M92 110 q8 -6 16 0 M132 110 q8 -6 16 0" fill="none" stroke="#3A2A22" stroke-width="3" stroke-linecap="round"/>'
        '<ellipse cx="100" cy="128" rx="6.5" ry="8.5" fill="#1C2140"/><ellipse cx="140" cy="128" rx="6.5" ry="8.5" fill="#1C2140"/>'
        '<circle cx="102.5" cy="125" r="2.2" fill="#FFFFFF"/><circle cx="142.5" cy="125" r="2.2" fill="#FFFFFF"/>'
        '<circle cx="86" cy="150" r="9" fill="#E9826B" opacity="0.4"/><circle cx="154" cy="150" r="9" fill="#E9826B" opacity="0.4"/>'
        '<path d="M108 154 Q120 166 132 154" fill="none" stroke="#7A3B2E" stroke-width="3.5" stroke-linecap="round"/>'
    )
    if glasses:
        head.append(
            f'<g fill="none" stroke="{INK}" stroke-width="3"><circle cx="100" cy="128" r="15"/><circle cx="140" cy="128" r="15"/><path d="M115 126 H125"/></g>'
        )
    if cap:
        head.append(
            '<path d="M66 70 L120 48 L174 70 L120 92 Z" fill="#16204A" stroke="#0E1530" stroke-width="2"/><path d="M92 78 L92 94 C108 102 132 102 148 94 L148 78" fill="#22306A"/><path d="M120 70 L166 80 L166 104" fill="none" stroke="#F2B33D" stroke-width="3" stroke-linecap="round"/><circle cx="166" cy="108" r="5" fill="#F2B33D"/>'
        )
    tilt = ' transform="rotate(-9 120 150)"' if pose == "tilt" else ""
    return (
        f'<path d="M36 280 C36 222 78 204 120 204 C162 204 204 222 204 280 Z" fill="{outfit}" stroke="{INK}" stroke-width="2.5"/>'
        f'<path d="M100 206 L120 230 L140 206" fill="none" stroke="#FFFDF8" stroke-width="4" stroke-linecap="round" opacity="0.7"/>'
        f'{wave}<rect x="106" y="168" width="28" height="42" rx="12" fill="{skin}"/><g{tilt}>{"".join(head)}</g>'
    )


def companion_svg(variant: str) -> str:
    if variant == "blob":
        return (
            f'<g stroke="{INK}" stroke-width="2.5" stroke-linecap="round">'
            '<ellipse cx="100" cy="186" rx="44" ry="6" fill="#1C2140" opacity="0.12" stroke="none"/>'
            '<path d="M80 60 C74 44 70 36 66 28 M120 58 C128 44 132 36 136 28" fill="none"/>'
            '<path d="M78 164 C74 172 72 178 70 182 M100 166 V184 M122 164 C126 172 128 178 130 182" fill="none" stroke-width="6"/>'
            '<path d="M100 58 C150 58 166 104 152 140 C144 162 124 170 100 170 C76 170 56 162 48 140 C34 104 50 58 100 58 Z" fill="#A99BD6"/>'
            '<circle cx="100" cy="100" r="22" fill="#FFFFFF"/><circle cx="103" cy="102" r="10" fill="#1C2140" stroke="none"/>'
            '<path d="M88 128 Q100 138 112 128" fill="none" stroke="#7A3B2E" stroke-width="3"/></g>'
        )
    # the theme's moon creature (قمّور): a plump glowing crescent
    return (
        f'<g stroke="{INK}" stroke-width="2.5" stroke-linecap="round">'
        '<circle cx="100" cy="100" r="78" fill="#FCEFD2" opacity="0.35" stroke="none"/>'
        '<path d="M120 36 A64 64 0 1 0 164 132 A52 52 0 0 1 120 36 Z" fill="#F6D27A"/>'
        '<circle cx="84" cy="100" r="5" fill="#1C2140" stroke="none"/><circle cx="108" cy="104" r="5" fill="#1C2140" stroke="none"/>'
        '<circle cx="76" cy="118" r="7" fill="#E9826B" opacity="0.45" stroke="none"/>'
        '<path d="M88 122 Q97 130 106 122" fill="none" stroke="#7A3B2E" stroke-width="3"/>'
        '<path d="M58 112 C46 108 42 98 44 90 M142 142 C150 150 160 150 166 144" fill="none" stroke-width="5"/></g>'
    )


BACKDROPS: dict[str, str] = {
    "night": (
        '<rect width="480" height="480" fill="#1F2C63"/><rect width="480" height="220" fill="#16204A"/>'
        '<circle cx="360" cy="96" r="44" fill="#FCEFD2"/><circle cx="380" cy="84" r="40" fill="#16204A"/>'
        '<g fill="#F2B33D"><path d="M90 60 C92 74 96 78 110 80 C96 82 92 86 90 100 C88 86 84 82 70 80 C84 78 88 74 90 60 Z"/>'
        '<circle cx="170" cy="40" r="3"/><circle cx="300" cy="50" r="2.5"/><circle cx="40" cy="150" r="2.5"/><circle cx="440" cy="190" r="3"/></g>'
        '<path d="M0 330 C90 280 170 300 250 320 S400 290 480 310 L480 480 L0 480 Z" fill="#22306A"/>'
        '<path d="M380 300 L380 250 L410 226 L440 250 L440 300 Z" fill="#0E1530"/><rect x="402" y="258" width="16" height="18" rx="3" fill="#F2B33D"/>'
        '<path d="M0 380 C120 350 220 370 300 390 S430 370 480 380 L480 480 L0 480 Z" fill="#0E1530"/>'
    ),
    "garden": (
        '<rect width="480" height="480" fill="#FCEFD2"/><circle cx="96" cy="100" r="46" fill="#F2B33D"/>'
        '<path d="M0 300 C100 250 200 270 300 280 S420 250 480 260 L480 480 L0 480 Z" fill="#A9C7B1"/>'
        '<rect x="378" y="220" width="12" height="80" rx="5" fill="#6B4E34"/><circle cx="366" cy="210" r="30" fill="#7FA38A"/>'
        '<circle cx="400" cy="200" r="32" fill="#6E9579"/><circle cx="384" cy="176" r="26" fill="#7FA38A"/>'
        '<rect x="70" y="236" width="10" height="64" rx="4" fill="#6B4E34"/><circle cx="62" cy="228" r="24" fill="#6E9579"/>'
        '<circle cx="90" cy="222" r="24" fill="#7FA38A"/><circle cx="76" cy="202" r="20" fill="#6E9579"/>'
        '<path d="M0 370 C120 340 240 360 330 372 S440 356 480 362 L480 480 L0 480 Z" fill="#7FA38A"/>'
    ),
    "street": (
        '<rect width="480" height="480" fill="#FCEFD2"/><circle cx="400" cy="80" r="36" fill="#F2B33D"/>'
        '<path d="M20 330 V190 H150 V330 Z" fill="#E8D5B0" stroke="#C9B48A" stroke-width="3"/>'
        '<path d="M60 330 V270 A25 25 0 0 1 110 270 V330 Z" fill="#7FA38A"/><path d="M40 220 A15 15 0 0 1 70 220 V245 H40 Z M100 220 A15 15 0 0 1 130 220 V245 H100 Z" fill="#9DB8E8"/>'
        '<path d="M300 330 V170 H460 V330 Z" fill="#EADBB9" stroke="#C9B48A" stroke-width="3"/><path d="M350 330 V262 A30 30 0 0 1 410 262 V330 Z" fill="#E9826B"/>'
        '<rect x="226" y="250" width="12" height="80" rx="5" fill="#6B4E34"/><circle cx="232" cy="236" r="34" fill="#9FB7A3"/>'
        '<path d="M0 330 H480 V480 H0 Z" fill="#D9C7A0"/><path d="M0 390 C140 370 340 370 480 390 V480 H0 Z" fill="#C9B48A"/>'
    ),
    "room": (
        '<rect width="480" height="480" fill="#F3EAD8"/><path d="M170 60 A70 70 0 0 1 310 60 V230 H170 Z" fill="#CFE0EE" stroke="#C9B48A" stroke-width="6"/>'
        '<circle cx="270" cy="110" r="20" fill="#F2B33D"/><rect x="0" y="330" width="480" height="150" fill="#E7D8BC"/>'
        '<g fill="#9DB8E8" opacity="0.55"><rect x="0" y="330" width="60" height="60"/><rect x="120" y="330" width="60" height="60"/><rect x="240" y="330" width="60" height="60"/><rect x="360" y="330" width="60" height="60"/>'
        '<rect x="60" y="390" width="60" height="60"/><rect x="180" y="390" width="60" height="60"/><rect x="300" y="390" width="60" height="60"/><rect x="420" y="390" width="60" height="60"/></g>'
        '<rect x="20" y="250" width="120" height="80" rx="16" fill="#E9826B" opacity="0.8"/><rect x="340" y="250" width="120" height="80" rx="16" fill="#7FA38A" opacity="0.8"/>'
    ),
    "grad": (
        '<rect width="480" height="480" fill="#FBF6EC"/><path d="M0 40 Q240 110 480 40" fill="none" stroke="#9A620A" stroke-width="2"/>'
        '<path d="M30 46 L50 46 L40 70 Z" fill="#E9826B"/><path d="M90 60 L110 62 L98 86 Z" fill="#7FA38A"/><path d="M150 70 L172 72 L158 96 Z" fill="#A99BD6"/>'
        '<path d="M212 76 L234 76 L222 100 Z" fill="#F2B33D"/><path d="M274 76 L296 74 L286 98 Z" fill="#E9826B"/><path d="M336 70 L358 68 L348 92 Z" fill="#7FA38A"/>'
        '<path d="M398 60 L418 56 L412 80 Z" fill="#A99BD6"/><path d="M450 46 L470 44 L464 68 Z" fill="#F2B33D"/>'
        '<rect x="0" y="380" width="480" height="100" fill="#16204A"/><rect x="0" y="372" width="480" height="12" fill="#22306A"/>'
    ),
}


# ---- reading the prompt ------------------------------------------------------------------------


def _pick(options: tuple[str, ...], key: bytes) -> str:
    return options[hashlib.sha256(key).digest()[0] % len(options)]


def _color_in(text: str, table: dict[str, str], default: str) -> str:
    low = text.lower()
    hits = [(low.find(word), color) for word, color in table.items() if word in low]
    return min(hits)[1] if hits else default


def _section(prompt: str, name: str) -> str:
    m = re.search(rf"^{name}.*?$(.*?)(?=^[A-Z]{{4,}}|\Z)", prompt, re.M | re.S)
    return m.group(1) if m else ""


def read_prompt(req: ImageRequest) -> dict[str, Any]:
    p = req.prompt
    scene = _section(p, "SCENE").lower()
    outfit = _section(p, "OUTFIT")
    chars = _section(p, "CHARACTERS")
    backdrop = (
        "night"
        if re.search(r"\bnight\b|moonlit|moonlight", scene)
        else (
            "grad"
            if re.search(r"stage|hall|graduation|curtain", scene)
            else (
                "street"
                if re.search(r"street|gate|walk", scene)
                else ("garden" if re.search(r"garden|yard|playground|olive grove", scene) else "room")
            )
        )
    )
    area = "top"
    for key in (
        "TOP-RIGHT",
        "TOP-LEFT",
        "BOTTOM-RIGHT",
        "BOTTOM-LEFT",
        "RIGHT 38%",
        "LEFT 38%",
        "BOTTOM 30%",
        "TOP 30%",
    ):
        if key in p:
            area = key.split()[0].lower()
            break
    ref_bytes = req.refs[0].data if req.refs else b""
    others = re.search(r"Also in the picture: ([^.]*)", chars)
    n_others = 0
    if others:
        words = re.findall(r"\b(one|two|three|four|five|six)\b", others.group(1))
        n_others = min(
            3, 1 + others.group(1).count(",") + others.group(1).count(" and ") + (2 if words else 0)
        )
    return {
        "plate": "No children and no main characters" in chars,
        "cover": "FRONT COVER" in p,
        "backdrop": backdrop,
        "area": area,
        "girl": "She is a girl" in chars,
        "glasses": "same glasses" in chars,
        "hijab": bool(outfit) and "hijab" in outfit.lower() and "No hijab" not in outfit,
        "outfit": _color_in(outfit, COLOR_WORDS, "#5B6FC0"),
        "hijab_color": _color_in(outfit.lower().split("hijab")[0][-40:], HIJAB_COLORS, "#EFE3C8"),
        "companion": ("blob" if "THE COMPANION is the character in Image" in chars else "moon")
        if "THE COMPANION" in chars
        else "",
        "others": n_others,
        "skin": _pick(SKINS, ref_bytes[-64:]),
        "hair": _pick(HAIRS, ref_bytes[-32:]),
        "cap": "graduation cap" in outfit.lower(),
    }


def sheet_svg(req: ImageRequest, w: int, h: int) -> str:
    """Character sheet (three poses) or companion sheet (two poses) on cream paper."""
    p = req.prompt
    vw = round(480 * w / h)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} 480" width="{w}" height="{h}">',
        f'<rect width="{vw}" height="480" fill="#F6EEDC"/>',
    ]
    if "CHARACTER REFERENCE SHEET" in p:
        ref = req.refs[0].data if req.refs else b""
        skin, hair = _pick(SKINS, ref[-64:]), _pick(HAIRS, ref[-32:])
        hair_style = "short" if "He is a boy" in p else "long"
        hijab, glasses = "The parent chose a hijab" in p, "wears glasses" in p
        for i, pose in enumerate(("front", "wave", "tilt")):
            x = vw * (i + 0.5) / 3 - 120 * 1.3
            parts.append(
                f'<g transform="translate({x:.0f},{480 - 280 * 1.3 - 20:.0f}) scale(1.3)">'
                + kid_svg(
                    skin=skin,
                    hair=hair,
                    outfit="#22306A",
                    hair_style=hair_style,
                    hijab=hijab,
                    hijab_color="#7FA38A",
                    pose=pose,
                    cap=False,
                    glasses=glasses,
                )
                + "</g>"
            )
    else:
        for i in range(2):
            x = vw * (i + 0.5) / 2 - 100 * 1.6
            parts.append(
                f'<g transform="translate({x:.0f},{240 - 100 * 1.6:.0f}) scale(1.6)">'
                + companion_svg("blob")
                + "</g>"
            )
    parts.append(
        f'<rect width="{vw}" height="480" filter="url(#paper)"/>'
        '<defs><filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/>'
        '<feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.3  0 0 0 0.10 0"/></filter></defs></svg>'
    )
    return "".join(parts)


def compose_svg(req: ImageRequest, w: int, h: int) -> str:
    if "CHARACTER REFERENCE SHEET" in req.prompt or "companion character named" in req.prompt:
        return sheet_svg(req, w, h)
    info = read_prompt(req)
    seed = req.seed or 0
    vw = round(480 * w / h)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} 480" width="{w}" height="{h}">',
        '<defs><filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/>'
        '<feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.3  0 0 0 0.10 0"/></filter>'
        '<filter id="wash"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="7"/>'
        '<feDisplacementMap in="SourceGraphic" scale="6"/></filter></defs>',
        f'<svg viewBox="0 0 480 480" width="{vw}" height="480" preserveAspectRatio="xMidYMax slice">'
        f'<g filter="url(#wash)">{BACKDROPS[info["backdrop"]]}</g></svg>',
    ]
    if not info["plate"]:
        area = info["area"]
        kid_h = 330 if info["cover"] else 300
        cx = vw / 2
        if area in ("right", "top-right", "bottom-right"):
            cx = vw * 0.34
        elif area in ("left", "top-left", "bottom-left"):
            cx = vw * 0.66
        bottom = 480 if area not in ("bottom",) else 400
        pose = ("front", "wave", "tilt")[seed % 3]
        others = info["others"]
        for i in range(others):
            ox = cx + (1 if i % 2 else -1) * (150 + 70 * (i // 2)) * (w / h if w > h else 1)
            ox = min(max(ox, 70), vw - 70)
            scale = 0.95
            parts.append(
                f'<g transform="translate({ox - 120 * scale:.0f},{bottom - 280 * scale:.0f}) scale({scale})" opacity="0.95">'
                + kid_svg(
                    skin=SKINS[(i + 2) % len(SKINS)],
                    hair=HAIRS[(i + 1) % len(HAIRS)],
                    outfit=("#7FA38A", "#E0A43A", "#9DB8E8")[i % 3],
                    hair_style=("short", "long", "curly")[i % 3],
                    hijab=i == 1,
                    hijab_color="#A99BD6",
                    pose="front",
                    cap=False,
                    glasses=False,
                )
                + "</g>"
            )
        scale = kid_h / 280
        parts.append(
            f'<g transform="translate({cx - 120 * scale:.0f},{bottom - 280 * scale:.0f}) scale({scale:.3f})">'
            + kid_svg(
                skin=info["skin"],
                hair=info["hair"],
                outfit=info["outfit"],
                hair_style="long" if info["girl"] else "short",
                hijab=info["hijab"],
                hijab_color=info["hijab_color"],
                pose=pose,
                cap=info["cap"],
                glasses=info["glasses"],
            )
            + "</g>"
        )
        if info["companion"]:
            cs = 0.62
            comp_x = cx + 120 if cx < vw / 2 + 1 else cx - 250
            parts.append(
                f'<g transform="translate({comp_x:.0f},{bottom - 200 * cs - 10:.0f}) scale({cs})">'
                + companion_svg(info["companion"])
                + "</g>"
            )
    parts.append(f'<rect width="{vw}" height="480" filter="url(#paper)"/></svg>')
    return "".join(parts)


class SketchImageProvider:
    name = "sketch"
    model = "qamra-sketch-1"

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    async def _page_browser(self) -> Browser:
        if self._browser is None:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch()
        return self._browser

    async def aclose(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        w, h = aspect_px(req.aspect, TIER_PX[req.resolution])
        svg = compose_svg(req, w, h)
        browser = await self._page_browser()
        page = await browser.new_page(viewport={"width": w, "height": h})
        try:
            await page.set_content(f'<html><body style="margin:0">{svg}</body></html>')
            data = await page.screenshot(type="png", clip={"x": 0, "y": 0, "width": w, "height": h})
        finally:
            await page.close()
        units = {"images": 1, "px": float(max(w, h)), "refs": float(len(req.refs))}  # for cost projections
        cost = CostEntry(req.step, self.name, self.model, units, 0.0)
        return GeneratedImage(
            data, "image/png", cost, {"provider": self.name, "size": f"{w}x{h}", "seed": req.seed}
        )
