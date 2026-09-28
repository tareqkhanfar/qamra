"""Per-book budget guard (Addendum 3 §2.4).

Every paid call first reserves its estimated cost. If spent + reserved + estimate would pass the cap,
the call is refused with `BudgetExceeded`: generation stops, the book is flagged in admin, and pages
already drawn are kept. Reservation and check happen without an `await` in between, so parallel page
tasks cannot overshoot together.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from qamra_ai.errors import QamraError


class BudgetExceeded(QamraError):
    user_message_ar = "توقّف إنشاء الكتاب مؤقتًا لمراجعة الفريق. سنكمله قريبًا."
    user_message_en = "We paused this book for a quick team review and will finish it soon."


@dataclass
class Budget:
    cap_usd: float
    spent_usd: float = 0.0  # includes earlier runs of the same book (preview, redraws)
    reserved_usd: float = 0.0
    exceeded: bool = False

    @property
    def remaining_usd(self) -> float:
        return round(self.cap_usd - self.spent_usd - self.reserved_usd, 4)

    def check(self, estimate: float, label: str) -> None:
        if self.spent_usd + self.reserved_usd + estimate > self.cap_usd + 1e-9:
            self.exceeded = True
            raise BudgetExceeded(
                f"budget cap ${self.cap_usd:.2f} reached before {label} "
                f"(spent ${self.spent_usd:.3f}, next ≈ ${estimate:.3f})"
            )

    @asynccontextmanager
    async def reserve(self, estimate: float, label: str) -> AsyncIterator[None]:
        self.check(estimate, label)
        self.reserved_usd += estimate
        try:
            yield
        finally:
            self.reserved_usd = max(0.0, round(self.reserved_usd - estimate, 9))

    def add(self, usd: float) -> None:
        self.spent_usd += usd
