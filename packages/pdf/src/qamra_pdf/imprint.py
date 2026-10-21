"""The «عن قمرة» page printed in every book, and the book code on its back cover (owner, 2026-10-19).

Every book of every product (the stories, the class books and every activity-book volume) carries one page
at a fixed place, its last page (see each product's planner), with: the book code, large («QB-7K4M2»,
`qamra_core.book_codes`), the child's name and the product and part, a short warm line about Qamra, how to
reach us (phone, WhatsApp, email, the website, Facebook and Instagram), a QR that opens the book's contact
page on the site (`https://{domain}/b/{code}`: every link there is clickable, with the code prefilled),
«صُنِعَ هذا الكتابُ خِصّيصًا لِـ…», the month the book was made and «جميع الحقوق محفوظة © قمرة». The back cover prints
the code small near its bottom (`back_code_html`), so it reads without opening the book.

One design for every product, in the product's own colours and ornament (`LOOKS`): `about_html` returns the
page's content as a block that fills the box it is put in (each engine places it in its own page: the story
book's `_about_page.html.j2`, the class book's per-copy page, the activity books' `about-qamra` page type).
A render without a book (a sample, a proposal page) passes an `Imprint` without a code: the page then prints
no code card and its QR opens the site's general contact page (`/hello`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from qamra_pdf.arabic_names import fill_name

Lang = Literal["ar", "en"]
Gender = Literal["m", "f"]
Motif = Literal["stars", "notebook", "trail", "hearts", "khatam"]

_TEMPLATES = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

MONTHS_AR = (
    "كانون الثاني",
    "شباط",
    "آذار",
    "نيسان",
    "أيار",
    "حزيران",
    "تموز",
    "آب",
    "أيلول",
    "تشرين الأول",
    "تشرين الثاني",
    "كانون الأول",
)
MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_HINDI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# What the page says (reviewed by the language reviewer, 2026-10-19). `{name:gen}`: the child's name in the
# genitive, joined to «لِـ» (`arabic_names.fill_name`: «لِأبي بكر», «لِلمعتصم»).
TEXT: dict[Lang, dict[str, str]] = {
    "ar": {
        "title": "عن قمرة",
        "made_for": "صُنِعَ هذا الكتابُ خِصّيصًا لِـ{name:gen}",
        "code_label": "رمز الكتاب",
        "code_hint": "اذكروا هذا الرمز عند التواصل معنا أو عند طلب نسخة أخرى.",
        "warm": "في قمرة نصنع لكل طفل كتابًا يكون هو بطله، نكتبه ونرسمه بحبّ صفحةً صفحة.",
        "contact_title": "تواصلوا معنا",
        "phone": "هاتف",
        "whatsapp": "واتساب",
        "email": "البريد الإلكتروني",
        "website": "الموقع الإلكتروني",
        "facebook": "فيسبوك",
        "instagram": "إنستغرام",
        "qr": "امسحوا رمز QR للتواصل معنا أو لطلب نسخة أخرى من هذا الكتاب",
        "qr_general": "امسحوا رمز QR للتواصل معنا",
        "made_on": "تاريخ الإعداد: {month}",
        "rights": "جميع الحقوق محفوظة © قمرة {year}",
        "brand": "قمرة",
        "back_code": "رمز الكتاب",
    },
    "en": {
        "title": "About Qamra",
        "made_for": "This book was made especially for {name}",
        "code_label": "Book code",
        "code_hint": "Please mention this code when you contact us or order another copy.",
        "warm": "At Qamra, we make each child a book where they are the hero, and we write and illustrate "
        "it with love, page by page.",
        "contact_title": "Get in touch",
        "phone": "Phone",
        "whatsapp": "WhatsApp",
        "email": "Email",
        "website": "Website",
        "facebook": "Facebook",
        "instagram": "Instagram",
        "qr": "Scan to contact us or to order another copy of this book",
        "qr_general": "Scan to contact us",
        "made_on": "Made in {month}",
        "rights": "© {year} Qamra. All rights reserved.",
        "brand": "Qamra",
        "back_code": "Book code",
    },
}

# The product lines' names as the store sells them (content/store/catalog.yaml).
PRODUCTS: dict[str, tuple[str, str]] = {
    "magic": ("قمرة سحري", "Qamra Magic"),
    "custom": ("قمرة سحري بحكاية خاصة", "Qamra Magic with a custom story"),
    "classic": ("قمرة كلاسيك", "Qamra Classic"),
    "class": ("كتاب الصف", "Class book"),
    "workbook": ("دوسية التأسيس", "Foundation workbook"),
    "journey": ("رحلتي الأولى للتعلّم", "My First Learning Journey"),
    "family": ("مغامراتي مع عائلتي", "My Adventures with My Family"),
    "islamic": ("قلبي يعرف الله", "My Heart Knows Allah"),
    "colorbook": ("دفاتر التلوين والرسم", "Coloring & Drawing Books"),
}


def product_name(line: str | None, lang: Lang = "ar") -> str:
    names = PRODUCTS.get(line or "", PRODUCTS["magic"])
    return names[0] if lang == "ar" else names[1]


@dataclass(frozen=True)
class Contact:
    """How to reach Qamra (the admin's «التواصل والمعلومات» settings; these are the owner's own)."""

    phone: str = "+970595870228"  # calls
    whatsapp: str = "+972595870228"
    email: str = "info@qamra.app"
    domain: str = "qamra.app"
    facebook: str = "https://www.facebook.com/qamrabooks"
    instagram: str = "https://www.instagram.com/qamra.app/"

    @property
    def site(self) -> str:
        return self.domain.strip().removeprefix("https://").removeprefix("http://").strip("/") or "qamra.app"

    @property
    def facebook_text(self) -> str:
        """«facebook.com/qamrabooks»."""
        return (
            re.sub(r"^https?://(www\.)?", "", self.facebook.strip()).strip("/") or "facebook.com/qamrabooks"
        )

    @property
    def instagram_text(self) -> str:
        """«@qamra.app»."""
        handle = re.sub(r"^https?://(www\.)?instagram\.com/", "", self.instagram.strip()).strip("/@ ")
        return f"@{handle or 'qamra.app'}"


def phone_text(number: str) -> str:
    """«+970 59 587 0228»: grouped the way it is said on the phone (left to right in every language)."""
    digits = re.sub(r"\D", "", number)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 12 and digits[:3] in ("970", "972", "962"):
        return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:]}"
    return f"+{digits}" if digits else number.strip()


@dataclass(frozen=True)
class Imprint:
    """What one book's «عن قمرة» page and back cover print."""

    code: str = ""  # «QB-7K4M2»; "" for a sample (no code card, the QR opens /hello)
    child_name: str = ""
    gender: Gender = "m"
    product: str = ""  # the product line's name («دوسية التأسيس»)
    part: str = ""  # the volume, stage or story title («KG1 · الجزء الأول», «سلمى في أوّل يوم بالروضة»)
    lang: Lang = "ar"
    made_on: date | None = None
    contact: Contact = field(default_factory=Contact)

    @property
    def url(self) -> str:
        """What the QR opens: the book's contact page, or the general one."""
        base = f"https://{self.contact.site}"
        return f"{base}/b/{self.code}" if self.code else f"{base}/hello"

    def text(self, key: str) -> str:
        return TEXT[self.lang][key]

    def made_for(self) -> str:
        if not self.child_name.strip():
            return ""
        if self.lang == "ar":
            return fill_name(self.text("made_for"), "name", self.child_name.strip())
        return self.text("made_for").format(name=self.child_name.strip())

    def month(self) -> str:
        day = self.made_on or date.today()
        if self.lang == "ar":
            return f"{MONTHS_AR[day.month - 1]} {str(day.year).translate(_HINDI)}"
        return f"{MONTHS_EN[day.month - 1]} {day.year}"

    def year(self) -> str:
        year = str((self.made_on or date.today()).year)
        return year.translate(_HINDI) if self.lang == "ar" else year


@dataclass(frozen=True)
class Look:
    """A product's colours and ornament on its «عن قمرة» page."""

    ink: str  # text
    accent: str  # headings, icons, the frame
    soft: str  # light cards
    card: str  # the code card
    card_ink: str  # the code on it
    gold: str = "#E9A92B"
    paper: str = "#FFFDF8"
    motif: Motif = "stars"
    title_font: str = "Baloo Bhaijaan 2"
    text_font: str = "Noto Naskh Arabic"


# CMYK-safe colours from each product's own palette (design/tokens.json, render/covers.py LOOKS)
LOOKS: dict[str, Look] = {
    "story": Look(ink="#16204A", accent="#C98A1B", soft="#FCEFD2", card="#16204A", card_ink="#F2B33D"),
    "foundation": Look(
        ink="#1C2140", accent="#E0663F", soft="#FDE8DF", card="#1C2140", card_ink="#FFD36B", motif="notebook"
    ),
    "journey": Look(
        ink="#1C2140", accent="#2A8F60", soft="#E2F3EA", card="#1F5A46", card_ink="#FFE27A", motif="trail"
    ),
    "family": Look(
        ink="#1C2140", accent="#D2662A", soft="#FCEBDC", card="#303A6A", card_ink="#FFD36B", motif="hearts"
    ),
    "islamic": Look(
        ink="#1C2140",
        accent="#1F6B52",
        soft="#E8F2EC",
        card="#1F4A3C",
        card_ink="#F2C55C",
        gold="#C99A2E",
        motif="khatam",
        text_font="Scheherazade New",
    ),
    # «دفاتر التلوين والرسم»: the interior prints black only, so its info page is black and greys too
    "colorbook": Look(
        ink="#111111",
        accent="#111111",
        soft="#EFEFEF",
        card="#111111",
        card_ink="#FFFFFF",
        gold="#555555",
        paper="#FFFFFF",
    ),
}


def look_for(product: str) -> Look:
    """The look of a product line («workbook» is the foundation workbook; stories and class books share
    one)."""
    key = {
        "workbook": "foundation",
        "magic": "story",
        "classic": "story",
        "custom": "story",
        "class": "story",
    }
    return LOOKS.get(key.get(product, product), LOOKS["story"])


def _qr(url: str) -> Markup | None:
    from qamra_pdf.render import qr_svg  # render imports this module

    return qr_svg(url)


def about_html(
    imprint: Imprint,
    look: Look,
    *,
    lead: Markup | str | None = None,
    compact: bool = False,
    hero: str = "",
    hero_round: bool = False,
    hero_mm: float = 34.0,
) -> Markup:
    """The page's content: a block that fills its box (the caller's page sets the box at its safe area).
    `lead`: a few lines printed above it (the Islamic volumes' farewell, which this page took the place of).
    `compact`: smaller type for a square page. `hero`: the child's picture beside «صُنِعَ هذا الكتابُ…» (a file
    URI): their cut-out character, or with `hero_round` their portrait in a gold ring."""
    c = imprint.contact
    rows = [
        ("phone", imprint.text("phone"), phone_text(c.phone)),
        ("whatsapp", imprint.text("whatsapp"), phone_text(c.whatsapp)),
        ("email", imprint.text("email"), c.email),
        ("web", imprint.text("website"), c.site),
        ("facebook", imprint.text("facebook"), c.facebook_text),
        ("instagram", imprint.text("instagram"), c.instagram_text),
    ]
    html = _env.get_template("_about.html.j2").render(
        im=imprint,
        lk=look,
        s=TEXT[imprint.lang],
        rows=rows,
        qr=_qr(imprint.url),
        lead=lead,
        compact=compact,
        hero=hero,
        hero_round=hero_round,
        hero_mm=hero_mm,
        dir="rtl" if imprint.lang == "ar" else "ltr",
    )
    return Markup(html)  # nosec B704 (autoescaped template)


def back_code_html(imprint: Imprint | None, ink: str = "#16204A", *, cls: str = "") -> Markup:
    """The code, small, for the back cover: «رمز الكتاب QB-7K4M2» (nothing without a code)."""
    if imprint is None or not imprint.code:
        return Markup("")
    html = _env.get_template("_about_back_code.html.j2").render(im=imprint, ink=ink, cls=cls)
    return Markup(html)  # nosec B704 (autoescaped template)
