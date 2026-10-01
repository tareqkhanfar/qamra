"""Payment providers (CLAUDE.md §4, Addendum 4 §5): cash on delivery today, a card gateway later.

Checkout asks the provider for the chosen method. Cash on delivery needs nothing at ordering time: the order
starts unpaid and staff mark it paid on delivery. The card gateway is a disabled stub until Tareq picks a
provider (a paid service: his approval first); choosing it is refused with a friendly message.
"""

from dataclasses import dataclass
from typing import Protocol

from fastapi import APIRouter

from qamra_api.errors import ApiError
from qamra_core.db.models import Order, PaymentMethod, PaymentStatus


@dataclass(frozen=True)
class PaymentStart:
    status: PaymentStatus
    redirect_url: str | None = None  # a hosted payment page, for gateways that have one


class PaymentProvider(Protocol):
    method: PaymentMethod
    enabled: bool
    label_ar: str
    label_en: str

    def start(self, order: Order) -> PaymentStart: ...


class CashOnDelivery:
    method = PaymentMethod.cod
    enabled = True
    label_ar = "الدفع عند الاستلام"
    label_en = "Cash on delivery"

    def start(self, order: Order) -> PaymentStart:
        return PaymentStart(status=PaymentStatus.unpaid)  # paid to the courier; staff record it


class CardGatewayStub:
    """The card gateway's seat (to be chosen): disabled, refused at checkout, never offered to a customer."""

    method = PaymentMethod.card
    enabled = False
    label_ar = "الدفع بالبطاقة"
    label_en = "Card payment"

    def start(self, order: Order) -> PaymentStart:
        raise ApiError("payment_unavailable", 409)


PROVIDERS: dict[PaymentMethod, PaymentProvider] = {p.method: p for p in (CashOnDelivery(), CardGatewayStub())}


def provider_for(method: str) -> PaymentProvider:
    """The provider for a checkout's `payment`: a disabled or unknown one is refused before any order."""
    provider = PROVIDERS.get(PaymentMethod(method)) if method in PaymentMethod else None
    if provider is None or not provider.enabled:
        raise ApiError("payment_unavailable", 409)
    return provider


@dataclass(frozen=True)
class MethodView:
    method: str
    enabled: bool
    label_ar: str
    label_en: str


def methods() -> list[MethodView]:
    """The methods a customer can pay with: the enabled providers only (today, cash on delivery)."""
    on = [p for p in PROVIDERS.values() if p.enabled]
    return [MethodView(p.method.value, p.enabled, p.label_ar, p.label_en) for p in on]


router = APIRouter(prefix="/api/store", tags=["store"])


@router.get("/payment-methods")
async def payment_methods() -> list[MethodView]:
    """What checkout offers: cash on delivery (a disabled provider is never listed)."""
    return methods()
