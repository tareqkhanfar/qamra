"""«صوت أهلي» in the print files: a QR per story page only with the family-voice add-on, in the outer bottom
corner inside the 10 mm safe area, 18 mm + a 2 mm quiet zone, and readable from the print PDF at 300 DPI."""

from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from playwright.async_api import async_playwright

from qamra_ai.pipeline.assemble import AssemblyInputs, assemble_book
from qamra_ai.pipeline.book import BookInputs, run_book
from qamra_ai.pipeline.runtime import Runtime
from qamra_pdf import Brand

BRAND = Brand("قمرة", "Qamra", "qamra.app", "t", "t")
VOICE = "https://qamra.app/v/lqn98STtT10rWGkiEtwB"  # a 20-character listen token, as the API makes them
PX_PER_MM = 96 / 25.4


def _inputs(run, book_inputs: BookInputs, voice_url: str | None) -> AssemblyInputs:  # type: ignore[no-untyped-def]
    return AssemblyInputs(
        run=run,
        story=run.story.out,
        child=book_inputs.child,
        lang="ar",
        brand=BRAND,
        character_sheet=book_inputs.character_sheet,
        voice_url=voice_url,
    )


async def test_the_add_on_prints_a_readable_qr_on_every_story_page(
    rt: Runtime, book_inputs: BookInputs, tmp_path: Path
) -> None:
    run = await run_book(rt, book_inputs, mode="final")
    files = await assemble_book(_inputs(run, book_inputs, VOICE), tmp_path)
    assert files.interior_pdf is not None and files.preflight_passed, {
        k: v.to_dict() for k, v in files.preflight.items()
    }
    story = [p for p in files.spec.pages if p.kind == "story"]
    coded = [p for p in story if p.qr_url]
    beats = sorted({b for b in run.plan.beats if b > 0})
    assert len(coded) == len(beats)  # one per story beat: the text half of a spread carries it
    assert all(p.panel is not None or p.layout == "split" for p in coded)
    assert {p.qr_url for p in coded} == {f"{VOICE}/{b}" for b in beats}
    assert files.spec.cover.qr_url == VOICE  # the back cover opens the first page

    html = (tmp_path / "interior.html").read_text(encoding="utf-8")
    assert html.count('class="voice-qr"') == len(coded)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto((tmp_path / "interior.html").as_uri())
        boxes = await page.evaluate(
            """() => [...document.querySelectorAll('[data-qr]')].map(el => {
                 const sec = el.closest('section'), s = sec.getBoundingClientRect();
                 const b = el.getBoundingClientRect();
                 const c = el.querySelector('.code').getBoundingClientRect();
                 return {number: +el.dataset.qr, side: sec.className.includes('qr-left') ? 'left' : 'right',
                         left: b.left - s.left, right: s.right - b.right, bottom: s.bottom - b.bottom,
                         width: b.width, code: c.width};
               })"""
        )
        await browser.close()
    sides = {p.number: p.side for p in coded}
    for b in boxes:
        mm = {k: v / PX_PER_MM for k, v in b.items() if isinstance(v, float | int) and k != "number"}
        assert b["side"] == sides[b["number"]]
        outer = mm["left"] if b["side"] == "left" else mm["right"]
        assert abs(outer - 13) < 0.2 and abs(mm["bottom"] - 13) < 0.2  # 3 mm bleed + the 10 mm safe line
        assert abs(mm["code"] - 18) < 0.1 and abs(mm["width"] - 22) < 0.1  # 18 mm + 2 × 2 mm quiet zone

    first = min(coded, key=lambda p: p.number)
    pdf = pdfium.PdfDocument(str(files.interior_pdf))
    bitmap = pdf[first.number - 1].render(scale=300 / 72)  # the print resolution
    image = cv2.cvtColor(np.asarray(bitmap.to_pil().convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = image.shape[:2]
    corner = image[h // 2 :, : w // 2] if first.side == "left" else image[h // 2 :, w // 2 :]
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(corner)
    assert text == first.qr_url


async def test_books_without_the_add_on_print_no_qr(
    rt: Runtime, book_inputs: BookInputs, tmp_path: Path
) -> None:
    run = await run_book(rt, book_inputs, mode="final")
    files = await assemble_book(_inputs(run, book_inputs, None), tmp_path, proof=False, print_files=False)
    assert not any(p.qr_url for p in files.spec.pages) and files.spec.cover.qr_url is None
    html = (tmp_path / "interior.html").read_text(encoding="utf-8")
    assert "voice-qr" not in html.replace(".voice-qr", "") and "data-qr" not in html
