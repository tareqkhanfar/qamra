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
    "sku",
    "format",
    "size",
    "copies",
    "extras",
    "interior_file",
    "cover_file",
    "gift",  # Addendum 9: pack as a gift (no prices in the parcel) with this card message
    "gift_message",
    "insert_files",  # «مغامراتي مع عائلتي»: its sticker sheet and card-stock sheets, printed apart
)
# A family book's insert files (manifest item["inserts"]: name → storage key), each a PDF with its die lines
# on the optional-content layer «CutContour»; the labels tell the printer the paper.
INSERT_LABELS = {
    "stickers": "ورقة الملصقات (ورق لاصق مطفي، قصّ نصفي)",
    "card-money-recipes": "كرتون القصّ 250 غ: النقود والوصفات",
    "card-games-roles": "كرتون القصّ 250 غ: الألعاب والأدوار",
}


def batch_code(batch_id: uuid.UUID, batch_date: date) -> str:
    """Short and readable on the phone with the printer, e.g. PB-260928-3F2A."""
    return f"PB-{batch_date:%y%m%d}-{batch_id.hex[:4].upper()}"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, token_hash(token)


def item_format(options: dict[str, Any], addons: list[dict[str, Any]]) -> str:
    fmt = str(options.get("format") or "")
    if fmt == "softcover" and any(a.get("slug") == FORMAT_ADDON for a in addons):
        return "hardcover"
    return fmt


def item_copies(quantity: int, addons: list[dict[str, Any]]) -> int:
    extra = sum(int(a.get("qty", 1)) for a in addons if a.get("slug") == COPY_ADDON)
    return quantity * (1 + extra)


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
            ]
        )
    return ("﻿" + out.getvalue()).encode("utf-8")  # BOM: spreadsheet apps then read Arabic correctly
