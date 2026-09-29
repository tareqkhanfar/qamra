"""Children lists from the school (CLAUDE.md §8): CSV in, a preview with friendly row errors, then the import.

- Headers may be Arabic or English, in any order (see `COLUMNS`).
- Files saved by Excel as "CSV UTF-8" or as plain "CSV" (Windows-1256 on Arabic Windows) both read right,
  with commas, semicolons or tabs.
- Every row gets errors (it can't be imported) or warnings (it can), each in Arabic and English.
- `.xlsx` is not read: openpyxl is not a dependency (see docs/decisions.md); the school saves as CSV.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from qamra_api.validation import PHONE

MAX_CHILDREN = 60
MAX_FILE = 512 * 1024
AGE_MIN, AGE_MAX = 2, 10

COLUMNS: dict[str, tuple[str, ...]] = {
    "name": ("name", "child", "child name", "first name", "اسم الطفل", "الاسم", "اسم", "اسم الطفلة"),
    "gender": ("gender", "sex", "boy/girl", "الجنس", "النوع", "ولد/بنت"),
    "birth_year": ("birth year", "year of birth", "born", "سنة الميلاد", "مواليد", "سنة الولادة"),
    "age": ("age", "العمر", "السن"),
    "parent_name": ("parent", "parent name", "guardian", "guardian name", "اسم ولي الأمر", "ولي الأمر"),
    "phone": (
        "phone", "mobile", "parent phone", "whatsapp", "الجوال", "جوال", "جوال ولي الأمر", "رقم الجوال",
        "الهاتف", "هاتف", "رقم الهاتف", "موبايل", "واتساب",
    ),
    "email": (
        "email", "e-mail", "parent email", "البريد", "البريد الإلكتروني", "بريد ولي الأمر", "ايميل", "إيميل",
    ),
}  # fmt: skip
BOYS = {"m", "male", "boy", "b", "ذكر", "ولد", "ولد/ذكر", "صبي"}
GIRLS = {"f", "female", "girl", "g", "أنثى", "انثى", "بنت", "بنت/أنثى", "فتاة"}
TEMPLATE_HEADER = ["اسم الطفل", "الجنس", "سنة الميلاد", "اسم ولي الأمر", "جوال ولي الأمر", "بريد ولي الأمر"]
TEMPLATE_EXAMPLE = ["يوسف", "ولد", "2021", "خليل يوسف", "0599123456", ""]

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")
_NAME = re.compile(r"^[\w؀-ۿ' .-]+$")

Message = dict[str, str]  # {"ar": …, "en": …}


def _msg(ar: str, en: str) -> Message:
    return {"ar": ar, "en": en}


@dataclass
class Row:
    row: int  # the line number in the file (1 = the header)
    name: str = ""
    gender: str | None = None  # m | f
    birth_year: int | None = None
    parent_name: str | None = None
    phone: str | None = None
    email: str | None = None
    errors: list[Message] = field(default_factory=list)
    warnings: list[Message] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def out(self) -> dict[str, Any]:
        return {**{k: getattr(self, k) for k in self.__dataclass_fields__}, "ok": self.ok}


def _key(header: str) -> str | None:
    clean = " ".join(header.replace("*", "").replace("﻿", "").split()).strip().lower()
    for column, aliases in COLUMNS.items():
        if clean in aliases:
            return column
    return None


def decode(data: bytes) -> str:
    """UTF-8 (with or without BOM), else Windows-1256: what Arabic Excel writes for plain CSV."""
    if len(data) > MAX_FILE:
        raise ValueError("too_large")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1256", errors="replace")


def parse_csv(text: str) -> list[dict[str, str]]:
    """Rows as {column: value} for the columns we know; raises ValueError("no_columns") without a name."""
    sample = text[:4096]
    try:
        dialect: Any = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return []
    keys = [_key(h) for h in rows[0]]
    if "name" not in keys:
        raise ValueError("no_columns")
    return [{k: (cell or "").strip() for k, cell in zip(keys, r, strict=False) if k} for r in rows[1:]]


def _year(value: str, today: int) -> int | None:
    digits = value.translate(_DIGITS).strip()
    if not digits.isdigit():
        return None
    number = int(digits)
    if AGE_MIN <= number <= AGE_MAX:  # an age
        return today - number
    if today - AGE_MAX <= number <= today - AGE_MIN:  # a birth year
        return number
    return None


def phone_digits(value: str) -> str:
    """Arabic-Indic digits to ASCII, and only what a phone number is made of."""
    return re.sub(r"[^\d+]", "", value.translate(_DIGITS))


def check_row(values: dict[str, Any], row: int, today: int | None = None) -> Row:
    """One child from the school's list, with friendly reasons when something is missing or unclear."""
    today = today or date.today().year
    out = Row(row=row)
    name = " ".join(str(values.get("name") or "").split())
    if not name:
        out.errors.append(_msg("اسم الطفل فارغ.", "The child's name is empty."))
    elif len(name) > 40 or not _NAME.match(name):
        out.errors.append(_msg("اسم الطفل غير صالح (حروف فقط، 40 حرفًا على الأكثر).", "Invalid child name."))
    out.name = name[:40]
    gender = " ".join(str(values.get("gender") or "").split()).lower()
    out.gender = "m" if gender in BOYS else "f" if gender in GIRLS else None
    if out.gender is None:
        out.errors.append(_msg("الجنس غير واضح: اكتبوا ولد أو بنت.", "Gender is unclear: write boy or girl."))
    year = str(values.get("birth_year") or "") or str(values.get("age") or "")
    out.birth_year = _year(year, today)
    if out.birth_year is None:
        out.errors.append(
            _msg(
                f"سنة الميلاد أو العمر غير صحيح ({AGE_MIN}–{AGE_MAX} سنوات).",
                f"Birth year or age is invalid ({AGE_MIN}–{AGE_MAX} years).",
            )
        )
    parent = " ".join(str(values.get("parent_name") or "").split())[:120]
    out.parent_name = parent or None
    if not parent:
        out.warnings.append(_msg("اسم ولي الأمر فارغ.", "The parent's name is empty."))
    phone = phone_digits(str(values.get("phone") or ""))
    email = str(values.get("email") or "").strip().lower()
    if phone:
        if PHONE.match(phone) and len(phone.lstrip("+")) >= 9:
            out.phone = phone
        else:
            out.errors.append(
                _msg("رقم الجوال ناقص أو غير صحيح.", "The phone number is incomplete or wrong.")
            )
    if email:
        if _EMAIL.match(email):
            out.email = email
        else:
            out.errors.append(_msg("البريد الإلكتروني غير صحيح.", "The email address is wrong."))
    if not phone and not email:
        out.errors.append(_msg("أضيفوا جوال ولي الأمر أو بريده.", "Add the parent's phone or email."))
    return out


def preview(rows: list[dict[str, Any]], existing: list[str], today: int | None = None) -> list[Row]:
    """Every row checked; names already in the class or twice in the file are a warning (twins happen)."""
    checked = [check_row(values, i + 2, today) for i, values in enumerate(rows)]
    seen = {" ".join(n.split()) for n in existing}
    for r in checked:
        if r.name and r.name in seen:
            r.warnings.append(_msg("اسم مكرّر في الصف.", "This name is already in the class."))
        seen.add(r.name)
    return checked


def template_csv() -> bytes:
    """The list template: UTF-8 with a BOM, so Excel opens the Arabic headers correctly."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_HEADER)
    writer.writerow(TEMPLATE_EXAMPLE)
    return ("﻿" + buf.getvalue()).encode("utf-8")
