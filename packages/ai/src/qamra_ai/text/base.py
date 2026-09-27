"""Text provider interface: one structured call = system + user parts → validated Pydantic model."""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from qamra_ai.cost import CostEntry

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ImagePart:
    data: bytes
    mime: str


UserPart = str | ImagePart


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
        system: str,
        user: list[UserPart],
        schema: type[T],
        max_tokens: int = 16000,
    ) -> StructuredResult[T]: ...
