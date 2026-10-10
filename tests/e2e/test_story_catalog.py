"""Every story on sale, and «قمرة سحري» for a story with no «قمرة كلاسيك» template (owner, 2026-10-09).

«موسم الزيتون» and the other stories written on 2026-10-09 have no Classic template yet: the catalog lists
them with their Magic price and says «سحري فقط», their page explains it and still shows the story (its art,
summary, values, ages and pages), and a parent orders them as Magic from the page to the cart. No AI: the
drawing steps are finished by the e2e fixtures (docs/e2e.md).
"""

import re

from e2e_flow import (
    BASE_URL,
    approve_placeholder_character,
    call,
    finish_preview,
    fits,
    give_consent,
    new_child,
    query,
    upload_photo,
)
from playwright.sync_api import Page, expect

STORIES = {
    "first-day": "أوّل يوم في الروضة",
    "graduation": "يوم تخرّجي",
    "new-sibling": "ضيفنا الصغير",
    "moon-trip": "رحلة إلى القمر",
    "olive-season": "موسم الزيتون",
    "dream-boat": "قارب الأحلام",
    "star-keeper": "حارس النجوم",
    "neighborhood-friends": "أصدقاء الحارة",
}


def card(page: Page, name: str):  # type: ignore[no-untyped-def]
    return page.locator("a[href*='/stories/']").filter(has=page.get_by_role("heading", name=name, exact=True))


def test_the_catalog_lists_every_story_with_what_it_is_sold_as(page: Page) -> None:
    # a live Classic template for one story (and one style and look): only that story says «كلاسيك وسحري»
    call(page, "POST", "/api/e2e/classic-templates", {"theme": "first-day", "style": "watercolor"})
    page.goto(f"{BASE_URL}/ar/stories")
    for name in STORIES.values():
        expect(card(page, name)).to_have_count(1)
    olive = card(page, "موسم الزيتون")
    expect(olive).to_have_attribute("href", re.compile(r"/ar/stories/olive-season$"))
    expect(olive.get_by_text("سحري فقط", exact=True)).to_be_visible()
    expect(olive.get_by_text(re.compile(r"^من 139"))).to_be_visible()  # the Magic price
    first = card(page, "أوّل يوم في الروضة")
    for _ in range(
        18
    ):  # the site keeps the story list up to a minute (Next's data cache): wait for the template
        if first.get_by_text("كلاسيك وسحري", exact=True).count():
            break
        page.wait_for_timeout(5000)
        page.reload()
    expect(first.get_by_text("كلاسيك وسحري", exact=True)).to_be_visible()
    fits(page)

    # the Classic list keeps the stories it can't make yet, each with what it can be ordered as
    page.goto(f"{BASE_URL}/ar/stories?line=classic")
    expect(card(page, "موسم الزيتون").get_by_text("سحري فقط", exact=True)).to_be_visible()
    expect(card(page, "موسم الزيتون").get_by_text(re.compile(r"^من 139"))).to_be_visible()


def test_a_magic_only_story_page_shows_the_story_and_offers_magic(page: Page) -> None:
    page.goto(f"{BASE_URL}/ar/stories/olive-season")
    expect(page.get_by_role("heading", level=1, name="موسم الزيتون")).to_be_visible()
    expect(page.get_by_text(re.compile("يحمل طفلك سلّته الصغيرة"))).to_be_visible()  # the summary
    for chip in ("حبّ الأرض", "الصبر", "احترام الكبار", "3–6 سنوات"):
        expect(
            page.get_by_text(re.compile("^" + chip.replace("\u0651", "\u0651?") + "$")).first
        ).to_be_visible()
    expect(page.get_by_text(re.compile(r"^\d+ صفحة$")).first).to_be_visible()
    # never an empty box: the cover is a picture (the story's art or its illustration), the viewer real text
    expect(page.get_by_role("img", name=re.compile("غلاف|رسم توضيحي")).first).to_be_visible()
    expect(page.get_by_text("هذه الحكاية متوفرة الآن في «قمرة سحري» فقط", exact=False)).to_be_visible()
    classic = page.get_by_role("radio", name=re.compile("قمرة كلاسيك"))
    expect(classic).to_have_attribute("aria-disabled", "true")
    expect(classic).to_contain_text("غير متاح لهذه الحكاية")
    magic = page.get_by_role("radio", name=re.compile("قمرة سحري"))
    expect(magic).to_have_attribute("aria-checked", "true")
    expect(page.get_by_text("139 ₪", exact=True).first).to_be_visible()
    fits(page)

    page.get_by_role("button", name="أضيفوا للسلة").click()  # one tap: the child's details come from the cart
    page.wait_for_url("**/cart")
    expect(page.get_by_text(re.compile("موسم الزيتون")).first).to_be_visible()
    expect(page.get_by_text(re.compile("قمرة سحري")).first).to_be_visible()


def test_a_magic_olive_season_book_from_its_page_to_the_cart(page: Page) -> None:
    """The whole Magic flow for a story with no Classic template: the page's «جرّبوا المعاينة أولًا» carries the
    story, the line and the style; the story step shows olive season chosen; the preview, the format and the
    add-ons lead to the cart line «سلمى في موسم الزيتون»."""
    page.goto(f"{BASE_URL}/ar/stories/olive-season")
    page.get_by_role("radio", name=re.compile("سينمائي ثلاثي الأبعاد")).click()
    preview = page.get_by_role("link", name="جرّبوا المعاينة أولًا")
    expect(preview).to_have_attribute("href", re.compile(r"theme=olive-season&line=magic"))
    preview.click()
    page.wait_for_url("**/create**")
    assert query(page)["theme"] == "olive-season" and query(page)["line"] == "magic"

    expect(page.get_by_role("heading", name="من بطل الحكاية؟")).to_be_visible()
    new_child(page, label="اسم البطل", name="سلمى", gender="f", age=5)
    page.get_by_role("button", name="متابعة").click()
    give_consent(page)
    upload_photo(page)
    approve_placeholder_character(page, "نعم، تشبه سلمى")  # drawn in the style picked on the page
    skip = page.get_by_role("button", name="تخطّي — كتاب بدون صاحب")
    expect(skip).to_be_visible()
    skip.click()

    expect(page.get_by_text("سلمى في موسم الزيتون").first).to_be_visible()  # the story chosen on its page
    expect(page.get_by_role("group", name=re.compile("ماذا تحب سلمى؟"))).to_be_visible()  # Magic asks likes
    page.get_by_role("button", name="اكتبوا الحكاية").click()
    finish_preview(page)
    page.get_by_role("button", name="الصفحات جاهزة").click()
    page.get_by_role("radio", name=re.compile("غلاف مقوّى")).click()
    page.get_by_role("button", name="متابعة للطلب").click()
    page.get_by_role("button", name="أضيفوا للسلة").click()

    page.wait_for_url("**/cart")
    expect(page.get_by_text(re.compile("سلمى في موسم الزيتون")).first).to_be_visible()
    expect(page.get_by_text(re.compile("قمرة سحري")).first).to_be_visible()
    fits(page)
