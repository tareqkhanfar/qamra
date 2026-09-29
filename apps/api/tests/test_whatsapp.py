"""The WhatsApp adapter: manual links by default, a log sender, and Twilio built but disabled."""

import httpx
import pytest
from structlog.testing import capture_logs

from qamra_api.whatsapp import (
    LinkWhatsAppSender,
    LogWhatsAppSender,
    TwilioWhatsAppSender,
    WhatsAppMessage,
    WhatsAppNotApproved,
    make_sender,
)

MSG = WhatsAppMessage(
    to="970599123456", template="shipped", text="طلبكم QM-ABC123 في الطريق", order_code="QM-ABC123"
)
KEYS = {"twilio_account_sid": "AC123", "twilio_auth_token": "secret", "twilio_whatsapp_from": "+14155238886"}


async def test_the_default_is_the_manual_link() -> None:
    for name in (None, "", "links", "sms", "whatever"):
        sender = make_sender(name, KEYS)
        assert isinstance(sender, LinkWhatsAppSender)
        assert (await sender.send(MSG)).status == "manual"


async def test_the_log_sender_keeps_personal_data_out_of_the_logs() -> None:
    sender = make_sender("log")
    assert isinstance(sender, LogWhatsAppSender)
    with capture_logs() as logs:
        result = await sender.send(MSG)
    assert result.status == "logged" and sender.sent == [MSG]
    assert logs == [
        {"event": "whatsapp.logged", "template": "shipped", "order": "QM-ABC123", "log_level": "info"}
    ]
    assert "970599123456" not in repr(logs) and "الطريق" not in repr(logs)


async def test_twilio_is_selectable_but_sends_nothing_until_approved() -> None:
    calls: list[httpx.Request] = []
    sender = make_sender("twilio", KEYS)
    assert isinstance(sender, TwilioWhatsAppSender) and not sender.approved
    sender.transport = httpx.MockTransport(
        lambda r: calls.append(r) or httpx.Response(201, json={"sid": "SM1"})
    )
    with pytest.raises(WhatsAppNotApproved):
        await sender.send(MSG)
    assert calls == []  # not even a request


async def test_twilio_request_shape_once_approved() -> None:
    seen: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"sid": "SM42"})

    sender = TwilioWhatsAppSender(
        "AC123", "secret", "+14155238886", approved=True, transport=httpx.MockTransport(reply)
    )
    result = await sender.send(MSG)
    assert result.status == "sent" and result.message_id == "SM42"
    [req] = seen
    assert req.url.path == "/2010-04-01/Accounts/AC123/Messages.json"
    body = httpx.QueryParams(req.content.decode())
    assert body["From"] == "whatsapp:+14155238886" and body["To"] == "whatsapp:+970599123456"
    with pytest.raises(WhatsAppNotApproved):
        await TwilioWhatsAppSender("", "", "", approved=True).send(MSG)
