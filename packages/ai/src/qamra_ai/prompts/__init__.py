"""Versioned prompt templates. Load by name + version; never inline prompt strings in code."""

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PROMPTS_DIR = Path(__file__).parent

_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    undefined=StrictUndefined,
    trim_blocks=False,  # True glues the next line onto inline {% endif %}
    lstrip_blocks=True,
    keep_trailing_newline=False,
    # Prompts are plain text for the model, never rendered as HTML: HTML-escaping would corrupt them.
    autoescape=False,  # nosec B701
)

_BLANKS = re.compile(r"\n\s*\n(\s*\n)+")


def render(template: str, version: int = 1, **context: Any) -> str:
    """Render `prompts/<template>.v<version>.j2`."""
    text = _env.get_template(f"{template}.v{version}.j2").render(**context)
    return _BLANKS.sub("\n\n", text).strip()


def prompt_id(template: str, version: int = 1) -> str:
    return f"{template}.v{version}"
