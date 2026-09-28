"""Offline text provider: answers with a canned factory per schema (tests + dry runs)."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from qamra_ai.cost import CostEntry
from qamra_ai.text.base import Effort, StructuredResult, System, T, UserPart, system_text

Responder = Callable[[str, str, list[UserPart]], BaseModel]


class FakeTextProvider:
    """`responders` maps schema class name → fn(step, system, user) returning an instance."""

    name = "fake"

    def __init__(self, responders: dict[str, Responder] | None = None) -> None:
        self.responders: dict[str, Responder] = responders or {}
        self.calls: list[dict[str, Any]] = []

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
    ) -> StructuredResult[T]:
        text = system_text(system)
        self.calls.append(
            {"step": step, "model": model, "schema": schema.__name__, "system": system, "user": user}
        )
        responder = self.responders.get(schema.__name__)
        if responder is None:
            raise KeyError(f"FakeTextProvider has no responder for {schema.__name__}")
        value = responder(step, text, user)
        return StructuredResult(
            value=schema.model_validate(value.model_dump()),
            cost=CostEntry(step, self.name, "fake-text-1", {"calls": 1}, 0.0),
        )
