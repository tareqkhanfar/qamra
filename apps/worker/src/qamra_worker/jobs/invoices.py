"""Invoice PDFs (Addendum 4 §5), rendered when an order is confirmed and kept in private storage."""

import asyncio
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_core.db.models import Order, OrderItem, PaymentMethod
from qamra_core.db.store import Invoice
from qamra_core.storage import ObjectStorage
from qamra_pdf import InvoiceLine, InvoiceSpec
from qamra_pdf import render_invoice as render_invoice_pdf
from qamra_worker import context
from qamra_worker.jobs.books import brand, resolved_settings

log = structlog.get_logger()
FORMATS_AR = {
    "digital": "نسخة رقمية",
    "softcover": "غلاف ورقي",
    "hardcover": "غلاف مقوّى",
    "spiral": "تجليد حلزوني",
}


def invoice_spec(db: Session, invoice: Invoice) -> InvoiceSpec:
    order = db.get(Order, invoice.order_id)
    if order is None:
        raise ValueError("order missing")
    values = resolved_settings(db).values
    lines = []
    for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)):
        child = item.personalization.get("child_name")
        options = item.title.get("options", {})
        detail = " · ".join(
            x
            for x in (FORMATS_AR.get(str(options.get("format", ""))), f"كتاب {child}" if child else None)
            if x
        )
        name = str(item.title.get("name_ar", item.sku or ""))
        lines.append(
            InvoiceLine(name, detail, item.quantity, item.unit_price, item.unit_price * item.quantity)
        )
        for addon in item.addons:  # at list price; the order's discount is one line in the totals
            price = Decimal(str(addon.get("unit_price") or "0"))
            if addon.get("included") or price <= 0:
                continue
            qty = int(addon.get("qty", 1))
            lines.append(
                InvoiceLine(str(addon.get("name_ar") or addon["slug"]), detail, qty, price, price * qty)
            )
    company = str(values.get("company_name") or brand().name_ar)
    details = [str(values.get(k)) for k in ("company_address", "support_whatsapp") if values.get(k)]
    if values.get("company_tax_id"):
        details.append(f"الرقم الضريبي: {values['company_tax_id']}")
    shipping: dict[str, Any] = order.shipping
    return InvoiceSpec(
        number=invoice.number,
        issued=invoice.created_at.date(),
        order_code=order.code,
        company=company,
        company_details=details,
        customer=str(shipping.get("name", "")),
        customer_details=[
            str(x) for x in (shipping.get("phone"), shipping.get("city"), shipping.get("address")) if x
        ],
        currency=order.currency.value,
        lines=lines,
        subtotal=order.subtotal,
        discount=order.discount,
        delivery=order.delivery_fee,
        total=order.total,
        payment="الدفع عند الاستلام" if order.payment_method == PaymentMethod.cod else "بطاقة",
    )


def render_invoice_job(db: Session, storage: ObjectStorage, invoice_id: str) -> str:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise ValueError("invoice missing")
    spec = invoice_spec(db, invoice)
    with tempfile.TemporaryDirectory(prefix="qamra-invoice-") as tmp:
        pdf = asyncio.run(render_invoice_pdf(spec, Path(tmp) / "invoice.pdf"))
        key = f"invoices/{invoice.year}/{invoice.number}.pdf"
        storage.put(key, pdf.read_bytes(), "application/pdf")
    invoice.pdf_key = key
    db.commit()
    log.info("invoice.rendered", invoice=invoice.number)
    return key


def render_invoice(invoice_id: str) -> str:
    """RQ entry point (enqueued by the order admin when an order is confirmed)."""
    context.init_process()
    with context.db_session() as db:
        return render_invoice_job(db, context.storage(), invoice_id)
