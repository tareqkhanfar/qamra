"""«حكاية خاصة» through the API: the brief's checks and friendly errors, the book and its product."""

import uuid

from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession
from test_create_companion import _ready_child

from qamra_core.db.models import Book
from qamra_core.storage import ObjectStorage

BRIEF = {
    "occasion": "عيد ميلادها الخامس",
    "place": "بيت ستّي في نابلس",
    "loves": ["الكنافة", "الأرجوحة تحت الزيتونة"],
    "wish": "أن تبقى تحب مشاركة ألعابها",
    "family": [{"role": "ستّي", "name": "فاطمة"}, {"role": "خالو"}],
}


async def test_a_custom_story_is_checked_then_sold_as_its_own_product(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    child, character = await _ready_child(client, adb, storage)
    body = {"child_id": child["id"], "character_id": character, "theme": "custom", "line": "magic"}

    async def start(**change: object) -> tuple[int, dict]:  # type: ignore[type-arg]
        r = await client.post("/api/create/books", json={**body, **change})
        return r.status_code, r.json()

    status, out = await start()
    assert status == 422 and out["error"]["code"] == "custom_story_invalid"  # the custom base needs a brief
    status, out = await start(custom={**BRIEF, "loves": ["الكنافة"], "wish": "ا" * 121})
    assert status == 422 and out["error"]["details"]["fields"] == ["loves", "wish"]
    assert "الحكاية الخاصة" in out["error"]["message"]["ar"]
    status, out = await start(line="classic", custom=BRIEF)
    assert status == 422 and out["error"]["code"] == "custom_story_magic_only"
    status, out = await start(theme="graduation", custom=BRIEF)
    assert status == 422 and out["error"]["details"]["fields"] == ["theme"]
    status, out = await start(custom={**BRIEF, "place": "بيتنا، اتصلوا 0599123456", "wish": "بلا حرب"})
    assert status == 422 and out["error"]["code"] == "custom_story_unsafe"
    assert out["error"]["details"]["fields"] == ["place", "wish"]

    queue = Queue("generation", connection=app.state.rq_redis)
    status, out = await start(custom={**BRIEF, "wish": "  أن تبقى   تحب مشاركة ألعابها "})
    assert status == 201, out
    assert out["custom"] is True and out["theme"] == "custom" and out["problem"] is None
    assert (
        queue.jobs[-1].func_name == "qamra_worker.jobs.books.generate_book"
        and queue.jobs[-1].args[1] == "preview"
    )
    book = await adb.get(Book, uuid.UUID(out["id"]))
    assert book is not None and book.generation["custom"]["wish"] == "أن تبقى تحب مشاركة ألعابها"
    assert book.generation["custom"]["family"][1] == {"role": "خالو", "name": None}

    # a custom story is sold as «سحري بحكاية خاصة» (169₪), not as a theme book
    plain = await client.post(f"/api/create/books/{out['id']}/cart", json={"sku": "magic-hard-21"})
    assert plain.status_code == 404
    cart = await client.post(f"/api/create/books/{out['id']}/cart", json={"sku": "magic-custom-hard-21"})
    assert cart.status_code == 201, cart.text
    item = cart.json()["items"][0]
    assert (
        item["product"] == "magic-custom-story"
        and item["theme"] == "custom"
        and item["unit_price"] == "169.00"
    )

    theme_book = await client.post("/api/create/books", json={**body, "theme": "graduation"})
    wrong = await client.post(
        f"/api/create/books/{theme_book.json()['id']}/cart", json={"sku": "magic-custom-hard-21"}
    )
    assert wrong.status_code == 404  # and a theme book is never sold as a custom story

    book.flags = ["brief_unsafe"]  # the AI review stopped it in the worker: the parent is told why
    await adb.commit()
    assert (await client.get(f"/api/create/books/{out['id']}")).json()["problem"] == "brief_unsafe"
