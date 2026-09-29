"""Email templates (content/emails): Arabic and English, rendered to a subject, a plain-text body and HTML.

The wording lives in `messages.yaml`; `layout.html` is the shared frame. Values are filled as plain text
first, then placed into the HTML with autoescaping, so a name like "<b>" can never become markup.
"""

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from qamra_ai.pipeline.theme import CONTENT_DIR

EMAILS_DIR = CONTENT_DIR / "emails"
FOOTER = {
    "ar": "وصلتكم هذه الرسالة لأن لكم طلبًا أو كتابًا في {brand}.{support}",
    "en": "You're receiving this because you have an order or a book with {brand}.{support}",
}
SUPPORT = {"ar": " للمساعدة: {email}", "en": " Need help? {email}"}


@dataclass(frozen=True)
class Item:
    label: str
    url: str | None = None


@dataclass(frozen=True)
class Rendered:
    subject: str
    text: str
    html: str
    lines: list[str] = field(default_factory=list)


@cache
def messages(root: Path = EMAILS_DIR) -> dict[str, dict[str, dict[str, Any]]]:
    data = yaml.safe_load((root / "messages.yaml").read_text(encoding="utf-8")) or {}
    return {str(k): v for k, v in data.items()}


@cache
def _envs(root: Path = EMAILS_DIR) -> tuple[SandboxedEnvironment, SandboxedEnvironment]:
    text = SandboxedEnvironment(autoescape=False, undefined=StrictUndefined, keep_trailing_newline=False)
    html = SandboxedEnvironment(
        loader=FileSystemLoader(str(root)), autoescape=True, undefined=StrictUndefined, trim_blocks=True
    )
    return text, html


def render(
    template: str,
    lang: str,
    values: dict[str, Any],
    items: list[Item] | None = None,
    root: Path = EMAILS_DIR,
) -> Rendered:
    lang = lang if lang in ("ar", "en") else "ar"
    spec = messages(root)[template][lang]
    text_env, html_env = _envs(root)

    def fill(source: str) -> str:
        return text_env.from_string(source).render(**values).strip()

    subject = " ".join(fill(spec["subject"]).split())  # one header line, whatever the values hold
    lines = [fill(line) for line in spec["lines"]]
    button = None
    if spec.get("button"):
        button = {"label": fill(spec["button"]["label"]), "url": str(values[spec["button"]["link"]])}
    support = str(values.get("support_email") or "")
    footer = FOOTER[lang].format(
        brand=values["brand"], support=SUPPORT[lang].format(email=support) if support else ""
    )
    rows = items or []
    text_parts = [*lines]
    if rows:
        text_parts.append("\n".join(f"- {i.label}" + (f": {i.url}" if i.url else "") for i in rows))
    if button:
        text_parts.append(f"{button['label']}: {button['url']}")
    text_parts.append("—\n" + footer)
    html = html_env.get_template("layout.html").render(
        lang=lang,
        dir="rtl" if lang == "ar" else "ltr",
        align="right" if lang == "ar" else "left",
        subject=subject,
        brand=values["brand"],
        lines=lines,
        items=rows,
        button=button,
        footer=footer,
    )
    return Rendered(subject=subject, text="\n\n".join(text_parts) + "\n", html=html, lines=lines)
