import io
from decimal import Decimal

import pdfplumber
from sqlalchemy.orm import Session

from qamra_core.db.models import Currency, Order, OrderItem, PaymentMethod
from qamra_core.db.store import Invoice
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs.invoices import render_invoice_job


def test_invoice_pdf_is_rendered_and_stored(db: Session, storage: ObjectStorage) -> None:
    order = Order(
        code="QM-TEST23",
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("84"),
        discount=Decimal("6.90"),
        delivery_fee=Decimal("20"),
        total=Decimal("97.10"),
        shipping={"name": "أم ليان", "phone": "0591234567", "city": "البيرة", "address": "حي الجنان"},
        phone="0591234567",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            sku="classic-soft-21",
            title={"name_ar": "قمرة كلاسيك", "options": {"format": "softcover"}},
            personalization={"child_name": "ليان"},
            addons=[
                {
                    "slug": "gift-box",
                    "qty": 1,
                    "included": False,
                    "unit_price": "15.00",
                    "name_ar": "علبة هدية",
                },
                {
                    "slug": "digital-copy",
                    "qty": 1,
                    "included": False,
                    "unit_price": "0",
                    "name_ar": "نسخة رقمية",
                },
            ],
            quantity=1,
            unit_price=Decimal("69"),
            discount=Decimal("6.90"),
        )
    )
    invoice = Invoice(
        order_id=order.id, number="INV-2026-00001", year=2026, seq=1, currency=Currency.ILS, total=order.total
    )
    db.add(invoice)
    db.commit()
    key = render_invoice_job(db, storage, str(invoice.id))
    assert key == "invoices/2026/INV-2026-00001.pdf" and invoice.pdf_key == key
    with pdfplumber.open(io.BytesIO(storage.get(key))) as pdf:
        text = pdf.pages[0].extract_text() or ""
        size = (pdf.pages[0].width, pdf.pages[0].height)
    assert "INV-2026-00001" in text and "QM-TEST23" in text and "97.10" in text
    assert "15.00" in text and "84.00" in text  # the gift box is its own line; lines add up to the subtotal
    assert abs(size[0] - 595.3) < 2 and abs(size[1] - 841.9) < 2  # A4
