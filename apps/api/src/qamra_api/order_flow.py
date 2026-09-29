"""Moving orders along the existing status transitions (admin_orders.TRANSITIONS) from other admin tools.

Print batches move many orders at once (to `printing` when the files go to the printer, to `shipped` when the
parcels leave). An order may be a step or two behind (confirmed, generating): the walk records every step as
its own event, exactly as if staff had clicked through them, and never jumps over the allowed moves.
"""

import uuid
from collections import deque

from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.routers.admin_orders import TRANSITIONS
from qamra_core.db.models import AuditLog, Order, OrderStatus
from qamra_core.db.store import OrderEvent

DETOURS = frozenset({OrderStatus.cancelled, OrderStatus.reprint})  # never walked through automatically


def path(start: OrderStatus, goal: OrderStatus) -> list[OrderStatus] | None:
    """The shortest list of allowed moves from `start` to `goal` (empty when already there)."""
    if start == goal:
        return []
    seen = {start}
    queue: deque[tuple[OrderStatus, list[OrderStatus]]] = deque([(start, [])])
    while queue:
        status, steps = queue.popleft()
        for nxt in TRANSITIONS[status]:
            if nxt in seen or (nxt in DETOURS and nxt != goal):
                continue
            if nxt == goal:
                return [*steps, nxt]
            seen.add(nxt)
            queue.append((nxt, [*steps, nxt]))
    return None


def move(
    db: AsyncSession,
    order: Order,
    goal: OrderStatus,
    actor: uuid.UUID | None,
    note: str,
    data: dict[str, str],
) -> list[OrderStatus]:
    """Walk `order` to `goal`; returns the statuses passed (for the customer emails). Raises on no path."""
    steps = path(order.status, goal)
    if steps is None:
        raise ValueError(f"no path from {order.status.value} to {goal.value}")
    for step in steps:
        before = order.status
        order.status = step
        db.add(
            OrderEvent(
                order_id=order.id,
                actor_user_id=actor,
                kind="status",
                from_status=before,
                to_status=step,
                note=note,
                data=data,
            )
        )
        db.add(
            AuditLog(
                actor_user_id=actor,
                action="order.status_changed",
                entity_type="order",
                entity_id=str(order.id),
                data={"from": before.value, "to": step.value, **data},
            )
        )
    return steps
