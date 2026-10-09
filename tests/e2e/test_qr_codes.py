"""The printed QR codes, scanned and opened on a phone (owner, 2026-10-09: every QR in every book must work).

A real page is rendered as it prints (the activity books' engine, the story books' interior template), its QR
is scanned from a screenshot with OpenCV, and the decoded https://qamra.app/... link is opened on the local
stack (`E2E_BASE_URL` stands in for the domain):

- «رحلتي الأولى للتعلّم»: a stage 1 sounds page and a stage 2 letter page open their player, show the item and
  play its reviewed clip (loaded by `/api/e2e/journey-audio/{code}` from content/journey/clips, as the
  server's `qamra_worker.journey_voices` does);
- a story book with «أصوات العائلة»: the page's QR opens its listen page, which says kindly that the family
  hasn't recorded it yet (a visitor gets a way to sign in, the owner a button to record this very page); once
  the owner records it, a visitor scanning the code plays that voice; the back cover's code opens page 1.

No AI and no paid call (docs/e2e.md): placeholder art, the shipped clips, and a recording uploaded as a file.
"""

import base64
import os
import re
from pathlib import Path

import cv2
import numpy as np
import pytest
from e2e_flow import BASE_URL, call, preview_book
from PIL import Image
from playwright.sync_api import Browser, Page, expect

DOMAIN = os.environ.get("BRAND_DOMAIN", "qamra.app")
ROOT = Path(__file__).resolve().parents[2]
CLIPS = ROOT / "content/journey/clips"
GIRL_NAME = "ليان"


def scan(png: bytes) -> list[str]:
    """The QR codes in a screenshot, as a phone's camera would read them."""
    image = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    for detector in (cv2.QRCodeDetector(), cv2.QRCodeDetectorAruco()):
        ok, texts, _, _ = detector.detectAndDecodeMulti(image)
        found = [t for t in texts if t] if ok else []
        if found:
            return found
    return []


def local(url: str) -> str:
    """The decoded link on the local stack: it must be https on the brand's domain, never an IP or http."""
    assert url.startswith(f"https://{DOMAIN}/"), url
    return BASE_URL + url[len(f"https://{DOMAIN}") :]


def screenshot_qr(browser: Browser, html: Path, selector: str) -> list[str]:
    """Open a print HTML file like the PDF renderer does and scan the element that holds its QR."""
    context = browser.new_context(device_scale_factor=3)
    try:
        page = context.new_page()
        page.goto(html.as_uri())
        page.wait_for_load_state("networkidle")
        return scan(page.locator(selector).first.screenshot())
    finally:
        context.close()


# ---- «رحلتي الأولى للتعلّم» --------------------------------------------------------------------------------


def journey_page_html(stage: int, number: int, out: Path) -> Path:
    from qamra_workbook.pictures import LibraryStore
    from qamra_workbook.render.engine import book_html, build_pages
    from qamra_workbook.render.journey_order import stage_specs
    from qamra_workbook.render.registry import Assets
    from qamra_workbook.render.spec import Child

    assets = Assets(LibraryStore())
    book, _ = stage_specs(Child(GIRL_NAME, "f"), stage, domain=DOMAIN, numbers=[number], name_en="Layan")
    path = out / f"journey-s{stage}-p{number}.html"
    path.write_text(book_html(book, build_pages(book, assets), assets), encoding="utf-8")
    return path


@pytest.mark.parametrize(("stage", "number"), [(1, 28), (2, 30)])  # animal sounds; the letter أ
def test_a_journey_pages_qr_plays_its_sound(
    page: Page, browser: Browser, tmp_path: Path, stage: int, number: int
) -> None:
    from qamra_api.journey_audio import item

    urls = screenshot_qr(browser, journey_page_html(stage, number, tmp_path), ".qr-card, .en-qr")
    assert len(urls) == 1 and re.fullmatch(rf"https://{re.escape(DOMAIN)}/a/[a-z2-7]{{8}}", urls[0]), urls
    code = urls[0].rsplit("/", 1)[1]
    expected = item(code)
    assert expected is not None and (CLIPS / f"{code}.mp3").is_file()
    call(
        page, "POST", f"/api/e2e/journey-audio/{code}"
    )  # the reviewed clip, as the server's loader stores it

    page.goto(local(urls[0]))
    expect(page.get_by_role("heading", name=expected["title"])).to_be_visible()
    for word in expected["show"]:
        expect(page.get_by_text(word, exact=True).first).to_be_visible()
    play = page.get_by_role("button", name="شغّلوا الصوت")
    expect(play).to_be_visible()
    src = page.locator("audio").get_attribute("src")
    assert src and src.startswith(f"/api/a/{code}/audio?")
    got = page.evaluate(
        "async (u) => { const r = await fetch(u); return [r.status, r.headers.get('content-type')]; }", src
    )
    assert got == [200, "audio/mpeg"]
    expect(page.get_by_role("button", name="تشغيل الموسيقى")).to_have_count(0)  # no lullaby over the sound
    play.click()
    expect(page.get_by_role("button", name="أوقفوا الصوت")).to_be_visible()  # the browser plays it


# ---- a story book with «أصوات العائلة» --------------------------------------------------------------------


def story_page_html(listen_url: str, beat: int, text: str, out: Path) -> Path:
    """One story page of the interior as it prints, with its family-voice QR (as `assemble_book` sets it)."""
    from qamra_pdf import BookSpec, Brand, CoverSpec, PageSpec, Panel, TitleSpec, render_html

    def art(name: str, color: str, size: tuple[int, int] = (1200, 1200)) -> Path:
        path = out / name
        Image.new("RGB", size, color).save(path, quality=90)
        return path

    spec = BookSpec(
        lang="ar",
        title="لَيانُ وَحارِسُ النُّجومِ",
        child_name=GIRL_NAME,
        child_age=5,
        gender="f",
        brand=Brand("قمرة", "Qamra", DOMAIN, "", ""),
        title_page=TitleSpec(GIRL_NAME, "وَحارِسُ النُّجومِ", "خِصّيصًا لِليان", "", art("portrait.jpg", "#FCEFD2")),
        cover=CoverSpec(art("cover.jpg", "#F2B33D"), GIRL_NAME, "وَحارِسُ النُّجومِ", "", qr_url=listen_url),
        pages=[
            PageSpec(
                beat + 1,
                "story",
                "right" if beat % 2 else "left",
                "full",
                art("story.jpg", "#22306A"),
                text,
                Panel("top"),
                qr_url=f"{listen_url}/{beat}",
            )
        ],
    )
    path = out / "story.html"
    path.write_text(render_html("interior.html.j2", spec), encoding="utf-8")
    return path


def test_a_story_pages_family_voice_qr_before_and_after_the_family_records(
    page: Page, browser: Browser, tmp_path: Path
) -> None:
    book = preview_book(page, name=GIRL_NAME)
    ordered = call(page, "POST", f"/api/e2e/books/{book['book_id']}/family-voice")
    beat = ordered["beats"][0]
    voice = call(page, "GET", f"/api/books/{book['book_id']}/voice")
    listen_url = voice["listen_url"]
    text = next(p["text"] for p in voice["pages"] if p["beat"] == beat)

    urls = screenshot_qr(browser, story_page_html(listen_url, beat, text, tmp_path), "[data-qr]")
    assert urls == [f"{listen_url}/{beat}"] and listen_url.startswith(f"https://{DOMAIN}/v/")
    link = local(urls[0])

    visitor = browser.new_context(viewport={"width": 390, "height": 844}, locale="ar")
    try:
        guest = visitor.new_page()
        guest.goto(link)  # before anyone recorded: a kind word, the text, and a way in for the owner
        expect(guest.get_by_text("لم تسجّل العائلة صوتها لهذه الصفحة بعد", exact=False)).to_be_visible()
        expect(guest.get_by_text(text)).to_be_visible()
        expect(
            guest.get_by_role("link", name="هل هذا كتابكم؟ ادخلوا إلى حسابكم لتسجّلوا أصواتكم")
        ).to_be_visible()
        expect(guest.get_by_role("button", name="تشغيل")).to_have_count(0)
        expect(guest.get_by_role("link", name="سجّلوا صوتكم لهذه الصفحة")).to_have_count(0)

        page.goto(link)  # the owner, signed in: a button to record this very page
        record = page.get_by_role("link", name="سجّلوا صوتكم لهذه الصفحة")
        expect(record).to_be_visible()
        record.click()
        page.wait_for_url(re.compile(rf"/ar/books/{book['book_id']}/voice\?page={beat}$"))
        expect(page.get_by_text(text).first).to_be_visible()

        clip = next(CLIPS.glob("*.mp3")).read_bytes()  # a real, playable recording
        status = page.evaluate(
            """async ([url, b64]) => {
                 const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
                 const form = new FormData();
                 form.append('file', new Blob([bytes], {type: 'audio/mpeg'}), 'rec.mp3');
                 form.append('duration_ms', '3000');
                 form.append('voice', 'ماما');
                 const r = await fetch(url, {method: 'POST', body: form, credentials: 'same-origin',
                                             headers: {'X-Qamra-Client': 'web'}});
                 return r.status;
               }""",
            [f"/api/books/{book['book_id']}/voice/pages/{beat}", base64.b64encode(clip).decode()],
        )
        assert status == 201

        guest.goto(link)  # the same printed code now plays the family's voice
        expect(guest.get_by_text("بصوت ماما")).to_be_visible()
        expect(guest.get_by_text("لم تسجّل العائلة صوتها لهذه الصفحة بعد", exact=False)).to_have_count(0)
        guest.get_by_role("button", name="تشغيل").click()
        expect(guest.get_by_role("button", name="إيقاف مؤقت")).to_be_visible()

        guest.goto(local(listen_url))  # the back cover's code: the first story page
        guest.wait_for_url(re.compile(rf"/ar/v/[A-Za-z0-9_-]+/{ordered['beats'][0]}$"))
    finally:
        visitor.close()
