"""Browser acceptance check (phone viewport, Arabic first):
home → worlds → register → account → logout → protected redirect → wrong password → login → silent refresh
→ English → kindergarten demo request.

  uv run scripts/e2e_auth.py --base-url http://localhost:3000 [--screenshots out/e2e]
"""

import argparse
import asyncio
import time
from pathlib import Path

from playwright.async_api import Page, async_playwright, expect


async def shot(page: Page, folder: Path | None, name: str) -> None:
    if folder:
        await page.screenshot(path=str(folder / f"{name}.png"), full_page=True)


async def run(base: str, folder: Path | None) -> None:
    email = f"e2e-{int(time.time())}@example.com"
    password = "moonlight-2026"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = await ctx.new_page()
        form_alert = page.locator("form").get_by_role("alert")

        await page.goto(base + "/")
        await page.wait_for_url("**/ar")
        await expect(page.locator("html")).to_have_attribute("dir", "rtl")
        await shot(page, folder, "01-home")

        await expect(page.get_by_role("heading", level=1)).to_contain_text("طفلك البطل")
        await page.goto(base + "/ar/themes")
        await expect(page.get_by_role("heading", level=1)).to_have_text("عوالم الحكايات")
        await expect(page.get_by_role("link", name="أوّل يوم في الروضة").first).to_be_visible()
        await page.goto(base + "/ar/register")
        await page.get_by_label("الاسم").fill("أم سلمى")
        await page.get_by_label("البريد الإلكتروني").fill(email)
        await page.get_by_label("كلمة المرور", exact=True).fill("short")
        await page.get_by_role("button", name="إنشاء الحساب").click()
        await expect(form_alert).to_contain_text("كلمة المرور قصيرة")
        await page.get_by_label("كلمة المرور", exact=True).fill(password)
        await page.get_by_role("button", name="إنشاء الحساب").click()
        await page.wait_for_url("**/ar/account")
        await expect(page.get_by_role("heading", level=1)).to_have_text("أم سلمى")
        await expect(page.get_by_text("لا توجد كتب بعد")).to_be_visible()
        await shot(page, folder, "02-account")

        await page.get_by_role("button", name="تسجيل الخروج").click()
        await page.wait_for_url("**/ar")
        await page.goto(base + "/ar/account")
        await page.wait_for_url("**/ar/login?next=*")

        await page.get_by_label("البريد الإلكتروني").fill(email)
        await page.get_by_label("كلمة المرور", exact=True).fill("wrong-password")
        await page.get_by_role("button", name="دخول").click()
        await expect(form_alert).to_have_text("البريد الإلكتروني أو كلمة المرور غير صحيحة.")
        await shot(page, folder, "03-login-error")
        await page.get_by_label("كلمة المرور", exact=True).fill(password)
        await page.get_by_role("button", name="دخول").click()
        await page.wait_for_url("**/ar/account")

        # access cookie gone (expired) → the page refreshes the session silently
        await ctx.clear_cookies(name="qamra_at")
        await page.reload()
        await expect(page.get_by_role("heading", level=1)).to_have_text("أم سلمى")

        await page.get_by_role("link", name="English").first.click()
        await page.wait_for_url("**/en/account")
        await expect(page.locator("html")).to_have_attribute("dir", "ltr")
        await expect(page.get_by_text("No books yet")).to_be_visible()
        await shot(page, folder, "04-account-en")

        await page.goto(base + "/ar/kindergartens#demo")
        await page.get_by_label("اسم الروضة أو المدرسة").fill("روضة الاختبار")
        await page.get_by_label("اسمك").fill("أ. منى")
        await page.get_by_label("رقم الجوال (واتساب)").fill("+970 59 000 0000")
        await page.get_by_label("عدد الأطفال المتوقّع").fill("22")
        await page.get_by_role("button", name="أرسل الطلب").click()
        await expect(page.get_by_text("وصل طلبكم!")).to_be_visible()
        await shot(page, folder, "05-kg-lead")
        await browser.close()
    print(f"✓ auth e2e passed against {base} ({email})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:3000")
    ap.add_argument("--screenshots", type=Path)
    args = ap.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    asyncio.run(run(args.base_url.rstrip("/"), args.screenshots))


if __name__ == "__main__":
    main()
