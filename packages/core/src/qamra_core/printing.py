"""Print batches (CLAUDE.md §7 step 7, Phase 3): what the API and the worker share.

A batch groups the printed orders whose books an admin approved (one batch per day for families, one per
organization for kindergartens). When it is sent, its manifest is frozen: one line per book with the copies,
the format and the storage keys of the interior and cover PDFs. The printer gets a link token; only its
sha256 is stored, and every click turns into a signed URL of ≤ 15 minutes.
"""

import csv
import hashlib
import io
import secrets
import uuid
from datetime import date
from typing import Any

PRINTED_FORMATS = ("softcover", "hardcover", "spiral")
# add-ons that change what the printer makes (the rest are content or digital)
FORMAT_ADDON = "hardcover-upgrade"
COPY_ADDON = "extra-copy"
NOT_PRINTED_ADDONS = frozenset(
    {
        "dedication-page",
        "drawing-companion",
        "extra-character",
        "digital-copy",
        "parent-guide",
        "editable-files",
    }
)
FILE_KINDS = ("interior", "cover")
CSV_COLUMNS = (
    "n",
    "order",
    "book_code",  # «QB-7K4M2»: printed on the book's «عن قمرة» page and its back cover
    "sku",
    "format",
    "size",
    "copies",
    "extras",
    "interior_file",
    "cover_file",
    "gift",  # Addendum 9: pack as a gift (no prices in the parcel) with this card message
    "gift_message",
    "insert_files",  # the sheets printed apart: a sticker sheet, the family book's card stock, an answer key
    "binding",  # the product's binding (stapled, wire-o, spiral, perfect) when the order line froze it
    "print_spec",  # size, binding, pages and paper in words, e.g. «A4 · دفتر مدبّس · 32 صفحة · ورق 160 غ…»
)
# What a printed order line freezes of its product (`OrderItem.title["print"]`, at checkout), so the printer
# knows a stapled B/W coloring book from a Wire-O sketchbook: the format alone says softcover or spiral.
PRINT_FEATURES = ("size", "binding", "pages", "interior", "paper_gsm", "cover_gsm")
BINDING_LABELS = {
    "stapled": "دفتر مدبّس (تدبيس من المنتصف)",
    "wire-o": "سلك حلزوني Wire-O",
    "spiral": "تجليد حلزوني",
    "perfect": "تجليد كعب لاصق",
}
INTERIOR_LABELS = {"bw": "داخلي أبيض وأسود", "color": "داخلي ملوّن"}
# An activity book's insert files (manifest item["inserts"]: name → storage key). The family book, every
# journey stage and every «قلبي يعرف الله» volume has its sticker sheet; the family book also its card stock.
# Each sheet is a PDF with its die lines on the optional-content layer «CutContour»; the labels tell the
# printer the paper.
INSERT_LABELS = {
    "stickers": "ورقة الملصقات (ورق لاصق مطفي، قصّ نصفي)",
    "card-money-recipes": "كرتون القصّ 250 غ: النقود والوصفات",
    "card-games-roles": "كرتون القصّ 250 غ: الألعاب والأدوار",
    "answer-key": "مفتاح الإجابات (كتيّب منفصل)",
}
# The answer key the journey and Islamic jobs render goes to the printer only for a line that bought it
# (docs/plans/order-flows.md, «Add-ons: what is deactivated», F1); the other inserts are part of the book.
PAID_INSERTS = {"answer-key": frozenset({"printed-answer-key", "printed-parent-guide"})}


def batch_code(batch_id: uuid.UUID, batch_date: date) -> str:
    """Short and readable on the phone with the printer, e.g. PB-260928-3F2A."""
    return f"PB-{batch_date:%y%m%d}-{batch_id.hex[:4].upper()}"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, token_hash(token)


def print_spec_of(features: dict[str, Any] | None, options: dict[str, Any]) -> dict[str, Any]:
    """The product's print facts for a printed variant (empty for a digital one, or a product with none)."""
    if str(options.get("format") or "") not in PRINTED_FORMATS:
        return {}
    return {k: (features or {})[k] for k in PRINT_FEATURES if (features or {}).get(k) not in (None, "")}


def print_spec_label(spec: dict[str, Any] | None) -> str:
    """The print facts in the printer's words: «A4 · دفتر مدبّس (…) · 32 صفحة · ورق 160 غ · داخلي أبيض وأسود ·
    غلاف كرتون 300 غ»; "" when the line froze none (lines ordered before 2026-10-21)."""
    spec = spec or {}
    parts = [
        str(spec["size"]) if spec.get("size") else "",
        BINDING_LABELS.get(str(spec.get("binding") or ""), str(spec.get("binding") or "")),
        f"{spec['pages']} صفحة" if spec.get("pages") else "",
        f"ورق {spec['paper_gsm']} غ" if spec.get("paper_gsm") else "",
        INTERIOR_LABELS.get(str(spec.get("interior") or ""), ""),
        f"غلاف كرتون {spec['cover_gsm']} غ" if spec.get("cover_gsm") else "",
    ]
    return " · ".join(p for p in parts if p)


def item_format(options: dict[str, Any], addons: list[dict[str, Any]]) -> str:
    fmt = str(options.get("format") or "")
    if fmt == "softcover" and any(a.get("slug") == FORMAT_ADDON for a in addons):
        return "hardcover"
    return fmt


def item_copies(quantity: int, addons: list[dict[str, Any]]) -> int:
    extra = sum(int(a.get("qty", 1)) for a in addons if a.get("slug") == COPY_ADDON)
    return quantity * (1 + extra)


def item_inserts(files: dict[str, Any], addons: list[dict[str, Any]]) -> dict[str, Any]:
    """The book's insert files the printer makes for this line (name → storage key)."""
    bought = {str(a.get("slug")) for a in addons}
    return {
        name: key for name, key in files.items() if not PAID_INSERTS.get(name) or PAID_INSERTS[name] & bought
    }


def item_extras(addons: list[dict[str, Any]]) -> list[str]:
    return [
        str(a["slug"]) + (f"×{a['qty']}" if int(a.get("qty", 1)) > 1 else "")
        for a in addons
        if a.get("slug") and a["slug"] not in NOT_PRINTED_ADDONS | {FORMAT_ADDON, COPY_ADDON}
    ]


def file_name(item: dict[str, Any], kind: str) -> str:
    return f"{int(item['n']):03d}-{item['order']}-{kind}.pdf"


def insert_file_name(item: dict[str, Any], name: str) -> str:
    return file_name(item, f"insert-{name}")


def manifest_csv(manifest: dict[str, Any]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_COLUMNS)
    for item in manifest.get("items", []):
        writer.writerow(
            [
                item["n"],
                item["order"],
                item.get("book_code") or "",
                item.get("sku") or "",
                item.get("format") or "",
                item.get("size") or "",
                item["copies"],
                " ".join(item.get("extras") or []),
                file_name(item, "interior"),
                file_name(item, "cover"),
                "yes" if item.get("gift") else "",
                item.get("gift_message") or "",
                " ".join(insert_file_name(item, name) for name in item.get("inserts") or {}),
                item.get("binding") or "",
                item.get("print_spec") or "",
            ]
        )
    return ("﻿" + out.getvalue()).encode("utf-8")  # BOM: spreadsheet apps then read Arabic correctly
