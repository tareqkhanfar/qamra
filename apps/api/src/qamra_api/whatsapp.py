"""WhatsApp adapter interface (CLAUDE.md §4 Notifications, Phase 5). Nothing is sent automatically.

Addendum 9: email is the only automatic channel. Customer messages stay ready-to-send `wa.me` links that
staff open by hand (routers/admin_orders.py `whatsapp_links`). This module is the seam for later:

- `LinkWhatsAppSender` ("links", the default): sends nothing; the staff member sends the prepared link.
- `LogWhatsAppSender` ("log"): writes that a message would go out (template and order only: no phone,
  name or text in the logs).
- `TwilioWhatsAppSender` ("twilio"): the Twilio Messages API, built but **disabled**. It needs Tareq's
  approval and account (a paid service); until `approved=True` is passed by code that doesn't exist yet,
  `send` refuses, and `make_sender` never passes it.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

import httpx
import structlog

log = structlog.get_logger("qamra.api.whatsapp")
SenderName = Literal["links", "log", "twilio"]
TWILIO_API = "https://api.twilio.com/2010-04-01"


@dataclass(frozen=True)
class WhatsAppMessage:
    to: str  # the customer's number in international form, digits only (e.g. 970599000000)
    template: str  # messages.yaml key: confirmed, shipped…
    text: str
    order_code: str | None = None


@dataclass(frozen=True)
class WhatsAppResult:
    status: Literal["sent", "logged", "manual"]
    provider: str
    message_id: str | None = None


class WhatsAppNotApproved(RuntimeError):
    """Automatic WhatsApp is a paid service waiting for Tareq's approval."""


class WhatsAppSender(Protocol):
    name: str

    async def send(self, message: WhatsAppMessage) -> WhatsAppResult: ...


class LinkWhatsAppSender:
    name = "links"

    async def send(self, message: WhatsAppMessage) -> WhatsAppResult:
        return WhatsAppResult("manual", self.name)  # staff send the prepared wa.me link themselves


class LogWhatsAppSender:
    name = "log"

    def __init__(self) -> None:
        self.sent: list[WhatsAppMessage] = []

    async def send(self, message: WhatsAppMessage) -> WhatsAppResult:
        self.sent.append(message)
        log.info("whatsapp.logged", template=message.template, order=message.order_code)
        return WhatsAppResult("logged", self.name)


class TwilioWhatsAppSender:
    name = "twilio"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        *,
        approved: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.account_sid, self.auth_token, self.from_number = account_sid, auth_token, from_number
        self.approved = approved
        self.transport = transport

    async def send(self, message: WhatsAppMessage) -> WhatsAppResult:
        if not self.approved:
            raise WhatsAppNotApproved("automatic WhatsApp is off until Tareq approves Twilio")
        if not (self.account_sid and self.auth_token and self.from_number):
            raise WhatsAppNotApproved("Twilio is not configured")
        async with httpx.AsyncClient(transport=self.transport, timeout=15) as client:
            r = await client.post(
                f"{TWILIO_API}/Accounts/{self.account_sid}/Messages.json",
                auth=(self.account_sid, self.auth_token),
                data={
                    "From": f"whatsapp:+{self.from_number.lstrip('+')}",
                    "To": f"whatsapp:+{message.to.lstrip('+')}",
                    "Body": message.text,
                },
            )
        r.raise_for_status()
        return WhatsAppResult("sent", self.name, str(r.json().get("sid") or "") or None)


def make_sender(name: str | None, values: dict[str, object] | None = None) -> WhatsAppSender:
    """The sender for a name; anything unknown falls back to the manual links. Twilio stays disabled."""
    values = values or {}
    if name == "log":
        return LogWhatsAppSender()
    if name == "twilio":
        return TwilioWhatsAppSender(
            str(values.get("twilio_account_sid") or ""),
            str(values.get("twilio_auth_token") or ""),
            str(values.get("twilio_whatsapp_from") or ""),
        )
    return LinkWhatsAppSender()
