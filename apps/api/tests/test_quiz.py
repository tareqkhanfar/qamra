"""«أي كتاب يناسب طفلي؟» (Addendum 9 §1.3): the rules as data, their matching, and their admin editor."""

from decimal import Decimal

import pytest
from api_helpers import make_admin
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_api.store.quiz import QuizRule, gaps, match, seed_rules
from qamra_core.db.models import AppSetting

RULES = seed_rules().rules


def _pick(age: int, goal: str, pen: str | None = None) -> tuple[str, dict[str, str], str, dict[str, str]]:
    rule = match(RULES, age, goal, pen)  # type: ignore[arg-type]
    assert rule is not None
    return rule.product.slug, rule.product.options, rule.alternative.slug, rule.alternative.options


@pytest.mark.parametrize(
    ("age", "goal", "pen", "expected"),
    [
        (5, "gift", None, ("stories", {}, "family-adventures", {})),
        (3, "gift", None, ("stories", {}, "family-adventures", {})),
        (6, "family", None, ("family-adventures", {}, "stories", {})),
        (3, "learn", "yes", ("learning-journey", {"stage": "1"}, "stories", {})),
        (6, "learn", "no", ("learning-journey", {"stage": "1"}, "stories", {})),  # no pen yet: start easy
        (4, "learn", "yes", ("learning-journey", {"stage": "2"}, "foundation-workbook", {"level": "kg1"})),
        (5, "learn", "yes", ("foundation-workbook", {"level": "kg2"}, "learning-journey", {"stage": "3"})),
        (6, "learn", "yes", ("foundation-workbook", {"level": "kg2"}, "learning-journey", {"stage": "3"})),
    ],
)
def test_the_default_table(age: int, goal: str, pen: str | None, expected: tuple[object, ...]) -> None:
    assert _pick(age, goal, pen) == expected


def test_every_answer_has_a_recommendation_and_the_first_rule_wins() -> None:
    assert gaps(RULES) == []
    only_gifts = [r for r in RULES if r.goal == "gift"]
    assert {(g["goal"], g["pen"]) for g in gaps(only_gifts)} == {
        ("learn", "yes"),
        ("learn", "no"),
        ("family", None),
    }
    first = QuizRule.model_validate(
        {"goal": "learn", "product": {"slug": "stories"}, "alternative": {"slug": "stories"}}
    )
    assert match([first, *RULES], 4, "learn", "yes") is first
    pen_rule = next(r for r in RULES if r.pen == "no")  # a rule on the pen answer never guesses it
    assert match([pen_rule], 5, "learn", None) is None and match([pen_rule], 5, "learn", "no") is pen_rule


async def test_quiz_answers_with_catalog_prices(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    r = await client.get("/api/shop/quiz?age=4&goal=learn&pen=yes")
    assert r.status_code == 200 and r.headers["cache-control"] == "public, max-age=60"
    body = r.json()
    product, alternative = body["product"], body["alternative"]
    assert product["slug"] == "learning-journey" and product["options"] == {"stage": "2"}
    assert product["name_ar"] == "رحلتي الأولى — المحطة 2" and product["available"] is True
    assert Decimal(product["from_price"]) == Decimal("69")  # the cheapest printed copy, not the PDF
    assert alternative["slug"] == "foundation-workbook" and Decimal(alternative["from_price"]) == Decimal(
        "49"
    )
    story = (await client.get("/api/shop/quiz?age=5&goal=gift")).json()["product"]
    assert story["kind"] == "stories" and Decimal(story["from_price"]) == Decimal("69")
    jod = (await client.get("/api/shop/quiz?age=5&goal=gift&currency=JOD")).json()["product"]
    assert jod["currency"] == "JOD" and Decimal(jod["from_price"]) == Decimal("13")
    assert (await client.get("/api/shop/quiz?age=5&goal=sleep")).status_code == 422


async def test_shop_summary_reads_the_class_books(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    r = await client.get("/api/shop/summary")
    assert r.status_code == 200
    assert Decimal(r.json()["class_book_from"]) == Decimal("35") and r.json()["class_book_min_qty"] == 20


async def test_admin_edits_the_rules(client: AsyncClient, adb: AsyncSession) -> None:
    assert "+quiz_rules" in await seed_store(adb)
    assert "+quiz_rules" not in await seed_store(adb)  # seeded once; admin edits are never overwritten
    await make_admin(client, adb)
    r = await client.get("/api/admin/quiz-rules")
    assert r.status_code == 200 and r.json()["saved"] is True and len(r.json()["rules"]) == len(RULES)
    rules = r.json()["rules"]

    r = await client.put("/api/admin/quiz-rules", json={"rules": [x for x in rules if x["goal"] != "family"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "quiz_gaps"
    broken = [{**rules[0], "product": {"slug": "moon-rocket"}}, *rules[1:]]
    r = await client.put("/api/admin/quiz-rules", json={"rules": broken})
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["product:moon-rocket"]

    gift_first = {**rules[0], "product": {"slug": "coloring-book", "title_ar": "كتاب تلوين"}}
    r = await client.put("/api/admin/quiz-rules", json={"rules": [gift_first, *rules[1:]]})
    assert r.status_code == 200 and r.json()["saved"] is True
    row = await adb.get(AppSetting, "quiz_rules")
    assert row is not None and row.value["rules"][0]["product"]["slug"] == "coloring-book"
    answer = (await client.get("/api/shop/quiz?age=5&goal=gift")).json()["product"]
    assert answer["slug"] == "coloring-book" and answer["name_ar"] == "كتاب تلوين"


async def test_the_rules_need_the_prices_permission(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb, email="editor@example.com", roles=("editor",))
    assert (await client.get("/api/admin/quiz-rules")).status_code == 403
    r = await client.put("/api/admin/quiz-rules", json={"rules": [x.model_dump() for x in RULES]})
    assert r.status_code == 403
