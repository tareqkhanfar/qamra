import asyncio

import pytest

from qamra_ai.pipeline.budget import Budget, BudgetExceeded
from qamra_ai.pipeline.fakes import good_page_qa
from qamra_ai.pipeline.qa import evaluate


def test_good_page_passes() -> None:
    v = evaluate(good_page_qa(), expect_hero=True, expect_companion=True, threshold=0.75)
    assert v.passed and v.score > 0.9 and v.flags == ()


@pytest.mark.parametrize(
    ("change", "flag"),
    [
        ({"safe": False}, "unsafe"),
        ({"text_in_image": True}, "text_in_image"),
        ({"anatomy_ok": False}, "anatomy"),
        ({"hero_count": 2}, "hero_count"),
        ({"likeness": 3}, "face"),
    ],
)
def test_hard_fails(change: dict[str, object], flag: str) -> None:
    qa = good_page_qa().model_copy(update=change)
    v = evaluate(qa, expect_hero=True, expect_companion=True, threshold=0.1)
    assert not v.passed and flag in v.flags


def test_soft_problems_lower_the_score() -> None:
    qa = good_page_qa().model_copy(update={"likeness": 6, "outfit_ok": False, "text_space_ok": False})
    v = evaluate(qa, expect_hero=True, expect_companion=True, threshold=0.75)
    assert not v.passed and {"face", "outfit", "text_space"} <= set(v.flags)
    assert v.score == pytest.approx(0.45 * 0.6 + 0.10 + 0.10 + 0.05, abs=1e-3)


def test_plate_has_no_likeness_or_outfit() -> None:
    qa = good_page_qa().model_copy(update={"hero_count": 0, "likeness": 0, "outfit_ok": False})
    v = evaluate(qa, expect_hero=False, expect_companion=False, threshold=0.75)
    assert v.passed and v.score == pytest.approx(1.0)
    assert not evaluate(
        good_page_qa(), expect_hero=False, expect_companion=False, threshold=0.75
    ).passed  # hero drawn


def test_budget_blocks_the_call_that_would_cross_the_cap() -> None:
    b = Budget(cap_usd=0.20, spent_usd=0.15)
    b.check(0.05, "ok")
    with pytest.raises(BudgetExceeded):
        b.check(0.06, "page:3")
    assert b.exceeded


async def test_parallel_reservations_cannot_overshoot() -> None:
    b = Budget(cap_usd=0.25)
    admitted = 0

    async def call() -> None:
        nonlocal admitted
        try:
            async with b.reserve(0.08, "page"):
                admitted += 1
                await asyncio.sleep(0.01)
                b.add(0.08)
        except BudgetExceeded:
            pass

    await asyncio.gather(*(call() for _ in range(6)))
    assert admitted == 3 and b.spent_usd == pytest.approx(0.24) and b.reserved_usd == 0
