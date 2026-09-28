"""Text provider interface: one structured call = system + user parts → validated Pydantic model.

Prompt caching (Addendum 3 §1): long fixed parts go first and are marked cacheable.
- `SystemPart(text, cache=True)` caches the system prompt up to that block (rules, style, theme bible);
- a `CACHE` marker inside `user` caches everything before it (e.g. the book's reference images for QA).
Caching is a prefix match, so fixed parts must come before per-request parts.
"""

from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

from qamra_ai.cost import CostEntry

T = TypeVar("T", bound=BaseModel)
Effort = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ImagePart:
    data: bytes
    mime: str


@dataclass(frozen=True)
class CacheBreak:
    """Cache the conversation prefix up to (and including) the previous part."""


CACHE = CacheBreak()


@dataclass(frozen=True)
class SystemPart:
    text: str
    cache: bool = False


UserPart = str | ImagePart | CacheBreak
System = str | list[SystemPart]


def system_text(system: System) -> str:
    return system if isinstance(system, str) else "\n\n".join(p.text for p in system)


@dataclass(frozen=True)
class StructuredResult[M: BaseModel]:
    value: M
    cost: CostEntry


class TextProvider(Protocol):
    name: str

    async def structured(
        self,
        *,
        step: str,
        model: str,
        system: System,
        user: list[UserPart],
        schema: type[T],
        max_tokens: int = 16000,
        effort: Effort | None = None,
    ) -> StructuredResult[T]: ...
