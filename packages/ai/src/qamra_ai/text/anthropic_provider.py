"""Claude adapter: structured outputs via `messages.parse`, validated against a Pydantic schema.

- Prompt caching: `SystemPart(cache=True)` and the `CACHE` marker become `cache_control` breakpoints
  (5-minute TTL). A prefix below the model's minimum (Sonnet 5: 1024 tokens, Haiku 4.5: 4096) is simply
  not cached; it costs nothing extra.
- `effort` is sent only to models that accept it (never to Haiku 4.5).
- Server-side refusal fallbacks (`fallbacks: "default"`) are sent only to the models they exist for.
"""

import base64
from typing import Any

import anthropic

from qamra_ai.cost import CostEntry, anthropic_cost
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError
from qamra_ai.text.base import CacheBreak, Effort, ImagePart, StructuredResult, System, T, UserPart

_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_FALLBACK_MODELS = ("claude-opus-5", "claude-opus-5-5", "claude-fable-5", "claude-fable-5-1")
_EFFORT_MODELS = ("claude-sonnet-5", "claude-sonnet-4-6", "claude-opus-", "claude-fable-")
_EPHEMERAL = {"type": "ephemeral"}
MAX_BREAKPOINTS = 4


def _system(system: System) -> str | list[dict[str, Any]]:
    if isinstance(system, str):
        return system
    blocks: list[dict[str, Any]] = []
    for part in system:
        block: dict[str, Any] = {"type": "text", "text": part.text}
        if part.cache:
            block["cache_control"] = dict(_EPHEMERAL)
        blocks.append(block)
    return blocks


def _content(parts: list[UserPart]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for p in parts:
        if isinstance(p, CacheBreak):
            if blocks:
                blocks[-1]["cache_control"] = dict(_EPHEMERAL)
        elif isinstance(p, ImagePart):
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


def _count_breakpoints(system: str | list[dict[str, Any]], content: list[dict[str, Any]]) -> int:
    blocks = [*(system if isinstance(system, list) else []), *content]
    return sum(1 for b in blocks if "cache_control" in b)


def supports_effort(model: str) -> bool:
    return model.startswith(_EFFORT_MODELS)


def supports_fallbacks(model: str) -> bool:
    return model in _FALLBACK_MODELS


class AnthropicTextProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None, server_fallbacks: bool = True) -> None:
        if not api_key:
            raise ProviderConfigError("Anthropic key is not set (admin → settings → AI keys)")
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=4)
        self._fallbacks = server_fallbacks

    def request(
        self, *, model: str, system: System, user: list[UserPart], max_tokens: int, effort: Effort | None
    ) -> dict[str, Any]:
        sys_blocks = _system(system)
        content = _content(user)
        if _count_breakpoints(sys_blocks, content) > MAX_BREAKPOINTS:
            raise ProviderConfigError(f"more than {MAX_BREAKPOINTS} cache breakpoints in one request")
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": sys_blocks,
            "messages": [{"role": "user", "content": content}],
        }
        if effort and supports_effort(model):
            kwargs["output_config"] = {"effort": effort}
        return kwargs

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
        kwargs = self.request(model=model, system=system, user=user, max_tokens=max_tokens, effort=effort)
        resp: Any
        try:
            if self._fallbacks and supports_fallbacks(model):
                resp = await self._client.beta.messages.parse(
                    betas=[_FALLBACK_BETA], fallbacks="default", output_format=schema, **kwargs
                )
            else:
                resp = await self._client.messages.parse(output_format=schema, **kwargs)
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
