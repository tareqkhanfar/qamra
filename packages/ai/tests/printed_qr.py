"""The QR codes a print file carries, read back the way a phone reads them, and the routes they may open.

`qr_svg` (qamra_pdf.render) prints a QR as an inline vector: one `M{x} {y}h1v1h-1z` square per dark module.
`decode` rebuilds that matrix as a picture (with a 4-module quiet zone) and decodes it with OpenCV, so a
test checks what is printed, not what was meant. `route` says which web route of the site a URL opens:

- `/a/{code}`: an activity book's audio item (apps/web `[locale]/a/[code]`, the API's `/api/a/{code}`);
- `/v/{token}/{page}` and `/v/{token}`: a story page's «صوت أهلي» listen page, and the back cover's.

Shared by the product tests (packages/workbook/tests, packages/ai/tests, apps/api/tests).
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WEB_APP = ROOT / "apps/web/src/app/[locale]"
QR_SVG = re.compile(
    r'<svg viewBox="0 0 (\d+) \1" shape-rendering="crispEdges"><path d="([^"]*)" fill="#16204A"/></svg>'
)
_MODULE = re.compile(r"M(\d+) (\d+)h1v1h-1z")

# the web app's printed routes (kept in step with its page files by test_the_web_routes_match)
AUDIO_CODE = re.compile(r"[a-z2-7]{4,16}")  # apps/web [locale]/a/[code]/page.tsx
LISTEN_TOKEN = re.compile(r"[A-Za-z0-9_-]{16,64}")  # qamra_api.routers.voice_public.TOKEN
MAX_PAGE = 99  # apps/web [locale]/v/[token]/[page]/page.tsx


def decode(size: int, path: str) -> str:
    """The text of one printed QR (its SVG size and path), or "" when it doesn't scan. OpenCV's two
    detectors are tried at a few module sizes (each misses the odd perfect code a phone reads at once)."""
    modules = _MODULE.findall(path)
    assert _MODULE.sub("", path) == "", "the QR path holds something else than modules"
    grid = np.full((size + 16, size + 16), 255, np.uint8)  # an 8-module quiet zone
    for x, y in modules:
        grid[int(y) + 8, int(x) + 8] = 0
    detectors = [cv2.QRCodeDetector(), cv2.QRCodeDetectorAruco()]
    for scale in (4, 6, 8):
        image = cv2.resize(grid, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        for detector in detectors:
            text = detector.detectAndDecode(image)[0]
            if text:
                return str(text)
    return ""


def qr_urls(html: str) -> list[str]:
    """Every QR in the HTML, decoded, in order."""
    return [decode(int(m.group(1)), m.group(2)) for m in QR_SVG.finditer(html)]


def qr_by_page(html: str, attr: str = "data-page") -> dict[str, list[str]]:
    """The decoded QRs of each page, by the page's `attr` (the activity books' `data-page`, the story books'
    `data-number`), in the order of the HTML."""
    out: dict[str, list[str]] = {}
    marks = [(m.start(), m.group(1)) for m in re.finditer(rf'<section[^>]*?\s{attr}="([^"]+)"', html)]
    for m in QR_SVG.finditer(html):
        owner = next((name for at, name in reversed(marks) if at < m.start()), "?")
        out.setdefault(owner, []).append(decode(int(m.group(1)), m.group(2)))
    return out


def route(url: str, domain: str = "qamra.app") -> tuple[str, dict[str, str]] | None:
    """(route name, its parameters) for a URL the site serves on `https://{domain}`, else None (an IP, http,
    another host, a path no route takes, a code in the wrong format)."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != domain or parts.query or parts.fragment:
        return None
    path = parts.path
    if m := re.fullmatch(rf"/a/({AUDIO_CODE.pattern})", path):
        return "audio", {"code": m.group(1)}
    if m := re.fullmatch(rf"/v/({LISTEN_TOKEN.pattern})/(\d+)", path):
        page = int(m.group(2))
        return ("listen", {"token": m.group(1), "page": m.group(2)}) if 1 <= page <= MAX_PAGE else None
    if m := re.fullmatch(rf"/v/({LISTEN_TOKEN.pattern})", path):
        return "listen-start", {"token": m.group(1)}
    return None
