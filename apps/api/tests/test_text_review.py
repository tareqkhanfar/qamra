"""Staff review every story's words before «تأكيد» (docs/plans/admin-story-text-review.md): the queue marks
the books waiting, edits save at once with their history (old/new, who) and an id-only audit entry, the
instant screen asks for a note, «إعادة إخراج الملفات» renders the words, the confirmation records who and
tells the family, and only reviewers may do any of it. The parent's own edits stop at the final files."""

import json
import uuid
from decimal import Decimal

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Child,
    Classroom,
    Gender,
    Locale,
    Organization,
    PageStatus,
    Theme,
    User,
)
from qamra_core.db.portal import ClassBook, ClassBookPage
from qamra_core.db.text_review import BookTextEdit

STORY = {
    "title": "ليان في يومها الأول",
    "dedication": "إلى ليان",
    "pages": [{"index": 1, "text": "ذَهَبَتْ لَيَانُ إِلَى الرَّوْضَةِ."}, {"index": 2, "text": "ضَحِكَتْ لَيَانُ."}],
    "parents_lesson": "درس للأهل",
    "parents_questions": ["ماذا أحببتِ؟", "من صديقتكِ؟"],
    "blurb": "حكاية ليان",
}


def _jobs(app: FastAPI, queue: str = "generation") -> list[tuple[str, tuple[object, ...]]]:
    return [(j.func_name, j.args) for j in Queue(queue, connection=app.state.rq_redis).jobs]


async def _story_book(
    adb: AsyncSession,
    owner_id: uuid.UUID,
    status: BookStatus = BookStatus.in_review,
    *,
    line: str | None = "magic",
    sample: bool = True,
    extra: dict[str, object] | None = None,
) -> Book:
    theme = (await adb.execute(select(Theme).where(Theme.slug == "first-day"))).scalar_one_or_none()
    if theme is None:
        await upsert_themes(adb)
        theme = (await adb.execute(select(Theme).where(Theme.slug == "first-day"))).scalar_one()
    child = Child(guardian_user_id=owner_id, first_name="ليان", gender=Gender.f, birth_year=2021)
    adb.add(child)
    await adb.flush()
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=theme.version,
        created_by_user_id=owner_id,
        language=Locale.ar,
        art_style="watercolor",
        status=status,
        is_sample=sample,
        title=STORY["title"],
        dedication=STORY["dedication"],
        parent_message="نحبّكِ",
        story=dict(STORY),
        budget_usd=Decimal("3.00"),
        generation={"mode": "final", **({"line": line} if line else {}), **(extra or {})},
        preflight={"interior": {"passed": True}, "cover": {"passed": True}},
        pdf_interior_key="children/x/books/y/files/interior.pdf",
        pdf_cover_key="children/x/books/y/files/cover.pdf",
    )
    adb.add(book)
    await adb.flush()
    adb.add(BookPage(book_id=book.id, index=0, text=STORY["title"], original_text=STORY["title"]))
    for p in STORY["pages"]:  # type: ignore[attr-defined]
        adb.add(
            BookPage(
                book_id=book.id,
                index=p["index"],
                text=p["text"],
                original_text=p["text"],
                status=PageStatus.ok,
                image_key=f"children/{child.id}/books/{book.id}/raw/{p['index']:02d}.png",
            )
        )
    await adb.commit()
    return book


async def _admin_id(adb: AsyncSession, email: str = "admin@example.com") -> uuid.UUID:
    return (await adb.execute(select(User.id).where(User.email == email))).scalar_one()


async def test_story_books_wait_for_their_text_review_in_the_queue(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await make_admin(client, adb)
    me = await _admin_id(adb)
    story = await _story_book(adb, me)
    activity = await _story_book(adb, me, line="family")  # an activity book: no story words to review
    cards = {c["id"]: c for c in (await client.get("/api/admin/books?view=review")).json()}
    assert cards[str(story.id)]["text_review"] == "waiting"
    assert cards[str(activity.id)]["text_review"] is None
    detail = (await client.get(f"/api/admin/books/{story.id}")).json()
    assert detail["text_review"] == "waiting" and detail["text_editable"] is True
    assert detail["child"]["name"] == "ليان" and detail["child"]["gender"] == "f"  # for the grammar check
    assert detail["story"]["title"] == STORY["title"] and detail["parent_message"] == "نحبّكِ"
    assert detail["text_originals"]["title"] == STORY["title"] and detail["text_edits"] == []
    assert next(p for p in detail["pages"] if p["beat"] == 1)["text"] == "ذَهَبَتْ لَيَانُ إِلَى الرَّوْضَةِ."
    assert (await client.get(f"/api/admin/books/{activity.id}")).json()["text_editable"] is False


async def test_the_review_shows_the_gender_check(client: AsyncClient, adb: AsyncSession) -> None:
    """«تحقق من التذكير والتأنيث»: the worker's hints (`generation.gender_check`, flag `gender_check`) reach
    the review screen, next to the words they point at."""
    await make_admin(client, adb)
    me = await _admin_id(adb)
    hint = {"field": "page:2", "word": "ضَحِكَ", "context": "ضَحِكَ لَيَانُ.", "rule": "verb_before_name"}
    book = await _story_book(adb, me, extra={"gender_check": [hint]})
    book.flags = ["gender_check"]
    await adb.commit()
    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    assert detail["gender_check"] == [hint] and "gender_check" in detail["flags"]
    plain = await _story_book(adb, me)
    assert (await client.get(f"/api/admin/books/{plain.id}")).json()["gender_check"] == []


async def test_a_page_edit_keeps_its_history_and_reopens_a_confirmed_book(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await make_admin(client, adb)
    me = await _admin_id(adb)
    book = await _story_book(adb, me, BookStatus.approved)
    edited = "ذَهَبَتْ لَيَانُ   إِلَى\nالرَّوْضَةِ فَرِحَةً."  # tashkeel kept, spaces and lines folded
    r = await client.patch(f"/api/admin/books/{book.id}/pages/1", json={"text": edited})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["text"] == "ذَهَبَتْ لَيَانُ إِلَى الرَّوْضَةِ فَرِحَةً." and out["status"] == "in_review"
    assert "text_changed" in out["flags"] and _jobs(app) == []  # saved at once, rendered later
    page = (
        await adb.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 1))
    ).scalar_one()
    assert page.text == out["text"] and "admin_edited" in page.flags
    [edit] = (await adb.execute(select(BookTextEdit).where(BookTextEdit.book_id == book.id))).scalars()
    assert (edit.field, edit.beat, edit.kind) == ("page", 1, "edit") and edit.actor_user_id == me
    assert edit.old_text == STORY["pages"][0]["text"] and edit.new_text == out["text"]  # type: ignore[index]
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "admin.page_text_edited"))
    ).scalar_one()
    assert audit.actor_user_id == me and audit.entity_id == str(book.id) and audit.data["beat"] == 1
    assert "لَيَانُ" not in json.dumps(audit.data, ensure_ascii=False)  # the audit log never holds the words

    same = await client.patch(f"/api/admin/books/{book.id}/pages/1", json={"text": out["text"]})
    assert same.status_code == 200  # nothing changed: no new history row
    r = await client.post(f"/api/admin/books/{book.id}/pages/1/revert")
    assert r.status_code == 200 and r.json()["text"] == STORY["pages"][0]["text"]  # type: ignore[index]
    await adb.refresh(page)
    assert "admin_edited" not in page.flags
    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    assert [e["kind"] for e in detail["text_edits"]] == ["revert", "edit"]  # newest first
    assert detail["text_edits"][1]["actor"] and detail["text_edits"][1]["new_text"] == out["text"]
    assert (await client.patch(f"/api/admin/books/{book.id}/pages/0", json={"text": "x"})).status_code == 404


async def test_title_dedication_and_parents_page_edits_reach_the_story(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await make_admin(client, adb)
    book = await _story_book(adb, await _admin_id(adb))
    base = f"/api/admin/books/{book.id}/story"
    r = await client.patch(base, json={"field": "title", "text": " ليان   والقمر "})
    assert r.status_code == 200 and r.json()["text"] == "ليان والقمر"
    r = await client.patch(base, json={"field": "dedication", "text": "إلى ليان، نجمتنا"})
    assert r.status_code == 200
    r = await client.patch(base, json={"field": "parents_questions", "text": "ماذا أحببتِ؟\n\n  من رافقكِ؟ "})
    assert r.status_code == 200 and r.json()["text"] == "ماذا أحببتِ؟\nمن رافقكِ؟"
    assert (await client.patch(base, json={"field": "parent_message", "text": ""})).status_code == 200
    r = await client.patch(base, json={"field": "title", "text": "  "})
    assert r.status_code == 422  # a book always has a title
    await adb.refresh(book)
    assert book.title == "ليان والقمر" and book.story["title"] == "ليان والقمر"  # what the PDF prints
    assert book.dedication == book.story["dedication"] == "إلى ليان، نجمتنا"
    assert book.story["parents_questions"] == ["ماذا أحببتِ؟", "من رافقكِ؟"] and book.parent_message is None
    assert book.story["pages"] == STORY["pages"] and "text_changed" in book.flags
    cover = (
        await adb.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 0))
    ).scalar_one()
    assert cover.text == "ليان والقمر"  # the reader's cover

    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    assert detail["text_originals"]["title"] == STORY["title"]  # what «استرجاع» brings back
    r = await client.post(f"{base}/title/revert")
    assert r.status_code == 200 and r.json()["text"] == STORY["title"]
    await adb.refresh(book)
    assert book.title == STORY["title"]
    assert (await client.post(f"{base}/blurb/revert")).status_code == 404  # never edited


async def test_flagged_words_need_the_editors_note(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    book = await _story_book(adb, await _admin_id(adb))
    path = f"/api/admin/books/{book.id}/pages/2"
    r = await client.patch(path, json={"text": "زوروا www.example.com مع ليان"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "text_unsafe"
    assert r.json()["error"]["details"]["reasons"] == ["link"]
    note = "رابط موقع الروضة، بطلب الأهل"
    r = await client.patch(path, json={"text": "زوروا www.example.com مع ليان", "note": note})
    assert r.status_code == 200
    [edit] = (await adb.execute(select(BookTextEdit).where(BookTextEdit.book_id == book.id))).scalars()
    assert edit.note == note and edit.screen == ["link"]
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "admin.page_text_edited"))
    ).scalar_one()
    assert audit.data["screen_override"] == ["link"]


async def test_rerender_then_confirm_records_who_and_tells_the_family(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await make_admin(client, adb)
    parent = User(email="lian.mom@example.com", full_name="أم ليان", password_hash="x")
    adb.add(parent)
    await adb.flush()
    book = await _story_book(adb, parent.id, sample=False)
    await client.patch(f"/api/admin/books/{book.id}/pages/2", json={"text": "ضَحِكَتْ لَيَانُ كَثِيرًا."})
    r = await client.post(f"/api/admin/books/{book.id}/approve")
    assert r.status_code == 409 and r.json()["error"]["code"] == "text_not_rendered"
    assert (await client.post(f"/api/admin/books/{book.id}/rerender")).status_code == 202
    assert _jobs(app) == [("qamra_worker.jobs.books.rerender", (str(book.id),))]
    r = await client.post(f"/api/admin/books/{book.id}/rerender")
    assert r.status_code == 409 and r.json()["error"]["code"] == "busy"

    await adb.refresh(book)
    book.status, book.flags = BookStatus.in_review, []  # what the worker's render leaves
    await adb.commit()
    assert _jobs(app, "default") == []  # nothing told the family before «تأكيد»
    r = await client.post(f"/api/admin/books/{book.id}/approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"
    await adb.refresh(book)
    me = await _admin_id(adb)
    assert book.approved_by_user_id == me and book.approved_at is not None
    audit = (await adb.execute(select(AuditLog).where(AuditLog.action == "admin.book_approved"))).scalar_one()
    assert audit.data["text_reviewed"] is True and audit.data["text_edits"] == 1
    assert _jobs(app, "default") == [
        ("qamra_worker.jobs.notify.send_book_email", (str(book.id), "book_ready"))
    ]
    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    assert detail["text_review"] == "confirmed" and detail["approved_by"]


async def test_stopped_and_activity_books_are_not_rerendered_here(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await make_admin(client, adb)
    me = await _admin_id(adb)
    failed = await _story_book(adb, me, BookStatus.failed)
    r = await client.post(f"/api/admin/books/{failed.id}/rerender")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_ready"  # «متابعة التوليد» instead
    activity = await _story_book(adb, me, line="journey")
    assert (await client.post(f"/api/admin/books/{activity.id}/rerender")).status_code == 404
    r = await client.patch(f"/api/admin/books/{activity.id}/story", json={"field": "title", "text": "x"})
    assert r.status_code == 404


async def test_a_class_copy_shows_the_class_words_read_only(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    org = Organization(name="روضة الزيتون")
    adb.add(org)
    await adb.flush()
    room = Classroom(organization_id=org.id, name="البراعم")
    adb.add(room)
    await adb.flush()
    cb = ClassBook(classroom_id=room.id, organization_id=org.id, plan={"pages": [{"index": 1}, {"index": 2}]})
    adb.add(cb)
    await adb.flush()
    adb.add_all(
        [
            ClassBookPage(class_book_id=cb.id, index=1, scene_key="arrive", text="وصل البراعم إلى الروضة."),
            ClassBookPage(class_book_id=cb.id, index=2, scene_key="play", text="لعب ليان وسامي."),
            ClassBookPage(class_book_id=cb.id, index=3, scene_key="old", text="صفحة قديمة"),  # not planned
        ]
    )
    await adb.commit()
    copy = await _story_book(adb, await _admin_id(adb), line="class", extra={"class_book_id": str(cb.id)})
    detail = (await client.get(f"/api/admin/books/{copy.id}")).json()
    assert detail["text_review"] == "waiting" and detail["text_editable"] is False
    assert detail["class_pages"] == [
        {"index": 1, "text": "وصل البراعم إلى الروضة."},
        {"index": 2, "text": "لعب ليان وسامي."},
    ]
    assert (await client.patch(f"/api/admin/books/{copy.id}/pages/1", json={"text": "x"})).status_code == 404


async def test_only_reviewers_review_the_words(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    book = await _story_book(adb, await _admin_id(adb))
    calls = [
        ("PATCH", f"/api/admin/books/{book.id}/pages/1", {"text": "نص آخر"}),
        ("POST", f"/api/admin/books/{book.id}/pages/1/revert", None),
        ("PATCH", f"/api/admin/books/{book.id}/story", {"field": "title", "text": "عنوان"}),
        ("POST", f"/api/admin/books/{book.id}/story/title/revert", None),
        ("POST", f"/api/admin/books/{book.id}/rerender", None),
        ("POST", f"/api/admin/books/{book.id}/approve", None),
    ]
    await client.post("/api/auth/logout")
    await register(client, email="a.parent@example.com")  # a parent: no admin area at all
    for method, path, body in calls:
        r = await client.request(method, path, json=body)
        assert r.status_code == 403, (path, r.text)
    await client.post("/api/auth/logout")
    await make_admin(client, adb, email="support@example.com", roles=("support",))  # reads, can't review
    assert (await client.get(f"/api/admin/books/{book.id}")).status_code == 200
    for method, path, body in calls:
        r = await client.request(method, path, json=body)
        assert r.status_code == 403, (path, r.text)
    await adb.refresh(book)
    assert book.status == BookStatus.in_review and book.title == STORY["title"] and not book.flags
    assert (
        not (await adb.execute(select(BookTextEdit).where(BookTextEdit.book_id == book.id))).scalars().all()
    )


async def test_parents_stop_editing_once_the_final_files_are_made(
    client: AsyncClient, adb: AsyncSession
) -> None:
    me = await register(client)
    book = await _story_book(adb, uuid.UUID(me["id"]), BookStatus.preview, sample=False)
    path = f"/api/create/books/{book.id}/pages/1"
    assert (await client.patch(path, json={"text": "ذهبت ليان فرحة."})).status_code == 200  # the preview
    book.status = BookStatus.generating
    book.generation = {**book.generation, "mode": "final"}  # the ordered book is being drawn
    await adb.commit()
    r = await client.patch(path, json={"text": "نص آخر"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "text_locked"
    for status in (BookStatus.in_review, BookStatus.approved):
        book.status = status
        await adb.commit()
        r = await client.patch(path, json={"text": "نص آخر"})
        assert r.status_code == 409 and r.json()["error"]["code"] == "text_locked"
