"""Claude adapter: structured outputs via `messages.parse`, validated against a Pydantic schema."""

import base64
from typing import Any

import anthropic

from qamra_ai.cost import CostEntry, anthropic_cost
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError
from qamra_ai.text.base import ImagePart, StructuredResult, T, UserPart

_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _content(parts: list[UserPart]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for p in parts:
        if isinstance(p, ImagePart):
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": p.mime,
                        "data": base64.standard_b64encode(p.data).decode(),
                    },
                }
            )
        else:
            blocks.append({"type": "text", "text": p})
    return blocks


class AnthropicTextProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None, server_fallbacks: bool = True) -> None:
        if not api_key:
            raise ProviderConfigError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=4)
        self._fallbacks = server_fallbacks

    async def structured(
        self,
        *,
        step: str,
        model: str,
        system: str,
        user: list[UserPart],
        schema: type[T],
        max_tokens: int = 16000,
    ) -> StructuredResult[T]:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": _content(user)}],
            "output_format": schema,
        }
        resp: Any
        try:
            if self._fallbacks:
                resp = await self._client.beta.messages.parse(
                    betas=[_FALLBACK_BETA], fallbacks="default", **kwargs
                )
            else:
                resp = await self._client.messages.parse(**kwargs)
        except anthropic.BadRequestError as e:
            raise ProviderConfigError(f"claude rejected request: {e.message}") from e
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.NotFoundError,
        ) as e:
            raise ProviderConfigError(f"claude config error: {e.message}") from e
        except (
            anthropic.RateLimitError,
            anthropic.InternalServerError,
            anthropic.APIConnectionError,
        ) as e:
            raise ProviderError(f"claude error: {e}") from e

        if resp.stop_reason == "refusal":
            category = resp.stop_details.category if resp.stop_details else None
            raise ContentBlocked(f"claude refused ({category})")
        if resp.stop_reason == "max_tokens":
            raise InvalidOutput(f"claude hit max_tokens={max_tokens} on {step}")
        parsed = resp.parsed_output
        if parsed is None:
            raise InvalidOutput(f"claude returned no parsable output on {step}")

        u = resp.usage
        usage = {
            "input_tokens": u.input_tokens or 0,
            "output_tokens": u.output_tokens or 0,
            "cache_read_input_tokens": u.cache_read_input_tokens or 0,
            "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
        }
        served_by = resp.model or model
        cost = CostEntry(step, self.name, served_by, dict(usage), anthropic_cost(served_by, usage))
        return StructuredResult(value=parsed, cost=cost)
