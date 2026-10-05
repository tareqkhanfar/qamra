"""Assemble the ~20 s Qamra brand film (the home hero, and the source of the social reels): AI shots + code
shots + Arabic captions + end card, then its soundtrack.

    uv run python scripts/build_film.py [--ffmpeg PATH] [--sound-only]

Reads the AI shots and mockups in out/video/ (shot1.mp4, shot2.mp4, shot4.mp4, shot4-start.png, mock/,
mock3x2/) and writes out/video/qamra-film.{mp4,webm} (silent: the social kit cuts its reels from it) and the
poster. The last step (scripts/film_audio.py) mixes the soundtrack (music, sparkles, page turns and the voice)
and writes the home hero apps/web/public/photos/hero-reading.{mp4,webm} with sound, plus a music-only cut
(out/video/qamra-film-music.mp4). The site plays the hero muted (Photo.tsx); the sound is there for sharing.
--sound-only redoes just that last step on the film already in out/video/.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import film_audio
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "out/video"
PUBLIC = ROOT / "apps/web/public/photos"
W, H, FPS = 1440, 960, 24
FONTS = ROOT / "packages/pdf/src/qamra_pdf/fonts"
CAPTIONS = {  # shot → (headline, small line)
    "s1": ("قمرة", "حكايات بطلُها طفلُكم"),
    "s2": ("من صورة واحدة…", "شخصية تشبه طفلكم"),
    "s3": ("كتاب مطبوع", "طفلكم بطل كل صفحة"),
    "s4": ("وللروضات", "كتاب تخرّج لكل طفل"),
}
FFMPEG = "ffmpeg"


def run(*args: str) -> None:
    subprocess.run([FFMPEG, "-v", "error", "-y", *args], check=True)


def still_clip(png: Path, out: Path, seconds: float, zoom_to: float = 1.08) -> None:
    """A slow push-in on a still (Ken Burns)."""
    frames = round(seconds * FPS)
    vf = (
        f"scale={W * 2}:{H * 2},zoompan=z='1+({zoom_to}-1)*on/{frames}'"
        ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={W}x{H}:fps={FPS},format=yuv420p"
    )
    run(
        "-loop",
        "1",
        "-i",
        str(png),
        "-vf",
        vf,
        "-frames:v",
        str(frames),
        "-c:v",
        "libx264",
        "-crf",
        "16",
        str(out),
    )


def ai_clip(src: Path, out: Path, start: float, seconds: float) -> None:
    vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuv420p"
    run(
        "-ss",
        f"{start}",
        "-t",
        f"{seconds}",
        "-i",
        str(src),
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        str(out),
    )


CSS = f"""
@font-face {{ font-family: Baloo; src: url('{(FONTS / "BalooBhaijaan2-ExtraBold.ttf").as_uri()}'); }}
@font-face {{ font-family: Plex; src: url('{(FONTS / "IBMPlexSansArabic-SemiBold.ttf").as_uri()}'); }}
html, body {{ margin: 0; width: {W}px; height: {H}px; background: transparent; direction: rtl; }}
.cap {{ position: absolute; bottom: 64px; right: 0; left: 0; display: flex; justify-content: center; }}
.pill {{ text-align: center; color: #FFFDF8; background: rgba(14,21,51,.58); border-radius: 34px;
  padding: 10px 48px 18px; text-shadow: 0 2px 10px rgba(10,14,40,.6);
  box-shadow: 0 10px 40px rgba(10,14,40,.25); }}
.pill b {{ display: block; font: 800 78px/1.15 Baloo; }}
.pill span {{ display: block; font: 600 40px/1.4 Plex; margin-top: 6px; }}
"""

END_CSS = """
body { background: radial-gradient(ellipse at 50% 35%, #26336E 0%, #16204A 55%, #0E1533 100%);
  color: #FFFDF8; }
.logo { position: absolute; top: 70px; width: 100%; text-align: center; }
.logo img { width: 92px; height: 92px; border-radius: 22px; vertical-align: middle; }
.logo b { font: 800 92px/1 Baloo; vertical-align: middle; margin-right: 18px; color: #F2B33D; }
.row { position: absolute; top: 260px; width: 100%; display: flex; justify-content: center; gap: 44px; }
.card { width: 360px; text-align: center; font: 600 34px/1.3 Plex; }
.card img { width: 360px; height: 300px; object-fit: cover; border-radius: 22px;
  box-shadow: 0 16px 40px rgba(0,0,0,.45); display: block; margin-bottom: 20px; }
.url { position: absolute; bottom: 80px; width: 100%; text-align: center; font: 700 52px/1 Plex;
  direction: ltr; color: #F2B33D; letter-spacing: 1px; }
"""


async def captions() -> None:
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page(viewport={"width": W, "height": H})
        for key, (big, small) in CAPTIONS.items():
            f = V / f"cap-{key}.html"
            f.write_text(
                f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='cap'>"
                f"<div class='pill'><b>{big}</b><span>{small}</span></div></div></body></html>",
                encoding="utf-8",
            )
            await page.goto(f.as_uri(), wait_until="load")
            await page.evaluate("document.fonts.ready")
            await page.wait_for_timeout(300)
            await page.screenshot(path=str(V / f"cap-{key}.png"), omit_background=True)
        hard = (V / "mock/hardcover.png").as_uri()
        wb = (ROOT / "apps/web/public/workbooks/family-adventures/01.jpg").as_uri()
        kg = (V / "shot4-start.png").as_uri()
        logo = (ROOT / "apps/web/public/icon.svg").as_uri()
        end = f"""<html><head><meta charset="utf-8"><style>{CSS}{END_CSS}</style></head><body>
<div class="logo"><img src="{logo}"><b>قمرة</b></div>
<div class="row">
 <div class="card"><img src="{hard}">حكايات بطلها طفلكم</div>
 <div class="card"><img src="{wb}" style="object-position: top">دوسيات أنشطة</div>
 <div class="card"><img src="{kg}">كتب للروضات</div>
</div>
<div class="url">qamra.app</div></body></html>"""
        f = V / "endcard.html"
        f.write_text(end, encoding="utf-8")
        await page.goto(f.as_uri(), wait_until="load")
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(V / "endcard.png"))
        await b.close()


def caption_over(clip: str, cap: str, dur: float) -> None:
    """The caption fades in 0.5 s after the start and out 0.7 s before the end."""
    run(
        *("-i", str(V / f"{clip}.mp4"), "-loop", "1", "-t", f"{dur}", "-i", str(V / f"cap-{cap}.png")),
        "-filter_complex",
        f"[1:v]format=rgba,fade=t=in:st=0.5:d=0.5:alpha=1,fade=t=out:st={dur - 0.7}:d=0.4:alpha=1[c];"
        "[0:v][c]overlay=0:0:shortest=1,format=yuv420p",
        *("-c:v", "libx264", "-crf", "16", str(V / f"{clip}t.mp4")),
    )


def picture() -> None:
    asyncio.run(captions())
    hardcover = Image.open(V / "mock3x2/hardcover.png").convert("RGB")
    hardcover.resize((W, H), Image.Resampling.LANCZOS).save(V / "s3a.png")
    sp = Image.open(V / "mock/spread.png").convert("RGB")
    cw = round(sp.height * W / H)
    sp = sp.crop(((sp.width - cw) // 2, 0, (sp.width - cw) // 2 + cw, sp.height))
    sp.resize((W, H), Image.Resampling.LANCZOS).save(V / "s3b.png")
    ai_clip(V / "shot1.mp4", V / "c1.mp4", 0.0, 4.0)
    ai_clip(V / "shot2.mp4", V / "c2.mp4", 0.0, 5.0)
    still_clip(V / "s3a.png", V / "c3a.mp4", 2.7)
    still_clip(V / "s3b.png", V / "c3b.mp4", 2.8)
    ai_clip(V / "shot4.mp4", V / "c4.mp4", 0.3, 4.6)
    still_clip(V / "endcard.png", V / "c5.mp4", 3.4, zoom_to=1.03)
    for clip, cap, dur in (("c1", "s1", 4.0), ("c2", "s2", 5.0), ("c4", "s4", 4.6)):
        caption_over(clip, cap, dur)
    # shot 3: the cover, then the open book, one caption across both
    run(
        *("-i", str(V / "c3a.mp4"), "-i", str(V / "c3b.mp4"), "-filter_complex"),
        "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=2.2,format=yuv420p[v]",
        *("-map", "[v]", "-c:v", "libx264", "-crf", "16", str(V / "c3.mp4")),
    )
    caption_over("c3", "s3", 5.0)
    parts = ["c1t", "c2t", "c3t", "c4t", "c5"]
    durs = [4.0, 5.0, 5.0, 4.6, 3.4]
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(V / f"{p}.mp4")]
    chain, last, t = "", "[0:v]", 0.0
    for i in range(1, len(parts)):
        t += durs[i - 1] - 0.5
        out = f"[x{i}]"
        chain += f"{last}[{i}:v]xfade=transition=fade:duration=0.5:offset={t:.2f}{out};"
        last = out
    chain += f"{last}format=yuv420p[v]"
    film = V / "qamra-film.mp4"
    run(
        *inputs,
        *("-filter_complex", chain, "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "24"),
        *("-movflags", "+faststart", str(film)),
    )
    run(
        "-i",
        str(film),
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "36",
        "-row-mt",
        "1",
        "-an",
        str(V / "qamra-film.webm"),
    )
    run("-i", str(film), "-frames:v", "1", "-q:v", "3", str(V / "qamra-film-poster.jpg"))


def main() -> int:
    global FFMPEG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ffmpeg", default=None, help="ffmpeg binary (default: $FFMPEG, PATH, imageio-ffmpeg)")
    ap.add_argument("--sound-only", action="store_true", help="only redo the soundtrack and the hero files")
    a = ap.parse_args()
    FFMPEG = film_audio.find_ffmpeg(a.ffmpeg)
    if not a.sound_only:
        picture()
        shutil.copy2(V / "qamra-film-poster.jpg", PUBLIC / "hero-reading-poster.jpg")
    warnings = film_audio.report(film_audio.hero(FFMPEG, V / "qamra-film.mp4", V / "qamra-film.webm", PUBLIC))
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
