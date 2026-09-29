"""Email adapters (CLAUDE.md §4 notifications): one small interface, an SMTP sender on the standard library,
a logging sender for when no SMTP account is configured, and an in-memory fake for tests.

Nothing personal is logged: not the address, not the subject (it can hold a child's name), not the body.
"""

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Any, Protocol

import structlog

log = structlog.get_logger("qamra.worker.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str


class EmailSender(Protocol):
    name: str  # "smtp" | "log" | "fake": recorded on the notification's outcome

    def send(self, message: EmailMessage) -> None: ...


@dataclass
class SmtpEmailSender:
    host: str
    port: int
    username: str
    password: str
    security: str  # starttls | ssl | none
    from_addr: str
    from_name: str
    timeout: float = 20.0
    name: str = "smtp"

    def mime(self, message: EmailMessage) -> MimeMessage:
        msg = MimeMessage()
        msg["Subject"] = message.subject
        msg["From"] = formataddr((self.from_name, self.from_addr))
        msg["To"] = message.to
        msg["Date"] = formatdate(usegmt=True)
        msg["Message-ID"] = make_msgid(domain=self.from_addr.rsplit("@", 1)[-1] or None)
        msg.set_content(message.text)
        msg.add_alternative(message.html, subtype="html")
        return msg

    def send(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        smtp: smtplib.SMTP
        if self.security == "ssl":
            smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=context)
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
        with smtp:
            if self.security == "starttls":
                smtp.starttls(context=context)
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(self.mime(message))


class LogEmailSender:
    """No SMTP server set in the admin (dev, or before an account exists): only note that one would go out."""

    name = "log"

    def send(self, message: EmailMessage) -> None:
        log.info("email.logged_not_sent", reason="smtp_not_configured", chars=len(message.text))


@dataclass
class FakeEmailSender:
    """Tests and local runs: keeps every message in memory; `fail=True` simulates an SMTP error."""

    outbox: list[EmailMessage] = field(default_factory=list)
    fail: bool = False
    name: str = "fake"

    def send(self, message: EmailMessage) -> None:
        if self.fail:
            raise smtplib.SMTPServerDisconnected("fake outage")
        self.outbox.append(message)


def smtp_configured(values: dict[str, Any]) -> bool:
    return bool(str(values.get("smtp_host") or "").strip() and str(values.get("mail_from") or "").strip())


def sender_from_settings(values: dict[str, Any], brand_name: str) -> EmailSender:
    """The admin settings decide: an SMTP server when one is set, otherwise the logging sender."""
    if not smtp_configured(values):
        return LogEmailSender()
    return SmtpEmailSender(
        host=str(values["smtp_host"]).strip(),
        port=int(values.get("smtp_port") or 587),
        username=str(values.get("smtp_username") or ""),
        password=str(values.get("smtp_password") or ""),
        security=str(values.get("smtp_security") or "starttls"),
        from_addr=str(values["mail_from"]).strip(),
        from_name=str(values.get("mail_from_name") or "").strip() or brand_name,
    )
