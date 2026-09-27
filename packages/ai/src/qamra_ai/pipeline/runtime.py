"""What every step needs: providers, settings, the cost ledger, and a retrying image call."""

from dataclasses import dataclass, field

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from qamra_ai.config import Settings
from qamra_ai.cost import CostLedger
from qamra_ai.errors import ProviderError
from qamra_ai.image.base import GeneratedImage, ImageProvider, ImageRequest
from qamra_ai.text.base import StructuredResult, T, TextProvider, UserPart


@dataclass
class Runtime:
    settings: Settings
    text: TextProvider
    image: ImageProvider
    ledger: CostLedger = field(default_factory=CostLedger)

    async def draw(self, req: ImageRequest) -> GeneratedImage:
        """Image call with exponential backoff on transient errors; cost is always recorded."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(ProviderError),
            stop=stop_after_attempt(self.settings.image_max_attempts),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            reraise=True,
        ):
            with attempt:
                result = await self.image.generate(req)
        self.ledger.add(result.cost)
        return result

    async def ask(
        self, *, step: str, system: str, user: list[UserPart], schema: type[T], fast: bool = False
    ) -> T:
        model = self.settings.text_model_fast if fast else self.settings.text_model
        result: StructuredResult[T] = await self.text.structured(
            step=step, model=model, system=system, user=user, schema=schema
        )
        self.ledger.add(result.cost)
        return result.value
