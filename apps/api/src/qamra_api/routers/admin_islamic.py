"""«قلبي يعرف الله» (Addendum 10 §3.3, §10): the scholar's review, unit by unit and page by page.

    GET  /api/admin/islamic/review                          the volumes, their units' progress, open points
    GET  /api/admin/islamic/review/volumes/{volume}         units → pages (preview links), sources, history
    POST /api/admin/islamic/review/units/{unit}/submit      staff: to the scholar (and back after an edit)
    POST /api/admin/islamic/review/units/{unit}/approve     the scholar only
    POST /api/admin/islamic/review/units/{unit}/request-changes   the scholar only (a note is required)
    POST /api/admin/islamic/review/units/{unit}/notes       staff or the scholar
    PUT  /api/admin/islamic/review/decisions/{source}       the scholar's answer to a `scholar_decision` point
    GET/PUT /api/admin/islamic/review/me                    the scholar's printed name and consent to be named
    POST /api/admin/islamic/review/volumes/{volume}/previews   staff: render the volume's review pages
    GET  /api/admin/islamic/review/previews/{volume}/{n}    one page's PNG (0 = the cover), streamed
    GET  /api/admin/islamic/review/export                   what the page engine reads (islamic_review.py)

A decision needs the `scholar` staff role itself: the owner's "*" grants every permission but never stands in
for the scholar. A volume is on sale only while all its units are approved (the store's `scholar_gate`).
"""

import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.deps import AdminUser, SessionDep, StorageDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_core.db.islamic import (
    IslamicReviewer,
    IslamicReviewEvent,
    IslamicReviewPreview,
    IslamicScholarDecision,
    IslamicUnitReview,
    ReviewStatus,
)
from qamra_core.db.models import AuditLog, User
from qamra_core.db.store import StaffRole, UserStaffRole
from qamra_core.islamic_review import (
    CONTENT_DIR,
    VOLUME_NAMES_AR,
    VOLUMES,
    ReviewState,
    Unit,
    build_export,
    content_units,
    load_state,
    units_by_volume,
)
from qamra_core.permissions import SCHOLAR_ROLE, allowed
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/admin/islamic/review", tags=["admin"], dependencies=[Depends(require_admin)])

PREVIEW_JOB = "qamra_worker.jobs.islamic_book.render_review_previews"
PREVIEW_STALE = timedelta(minutes=30)  # a queued render older than this may be asked for again
S = ReviewStatus


# ---- the plan: pages and the sources they cite (read from content/islamic by the page engine's loader) -----


def _stamp(root: Path) -> float:
    return max((p.stat().st_mtime for p in root.rglob("*.yaml")), default=0.0)


@lru_cache(maxsize=2)
def _plan(stamp: float) -> Any:
    from qamra_workbook import islamic  # plan structure only: ids and references, never religious wording

    return islamic.load()


def plan() -> Any:
    return _plan(_stamp(CONTENT_DIR / "islamic"))


def _chain(sources: dict[str, dict[str, Any]], source_id: str) -> list[str]:
    """A source and the ones it stands on (a dua's hadith, a ruling's basis): their points reach the page."""
    out, todo = [], [source_id]
    while todo:
        current = todo.pop()
        src = sources.get(current)
        if src is None or current in out:
            continue
        out.append(current)
        todo += [
            *(src.get("basis") or []),
            *([src["dua"]["from"]] if isinstance(src.get("dua"), dict) else []),
        ]
    return out


# ---- who may do what ----------------------------------------------------------------------------------


async def _roles(db: AsyncSession, user: User) -> set[StaffRole]:
    rows = await db.execute(select(UserStaffRole.role).where(UserStaffRole.user_id == user.id))
    return set(rows.scalars())


async def require_scholar(user: AdminUser, db: SessionDep) -> User:
    """The scholar's own role (Addendum 10 §3.3), not a permission the owner's "*" would grant."""
    if SCHOLAR_ROLE not in await _roles(db, user):
        raise ApiError("scholar_only", 403)
    return user


ScholarUser = Annotated[User, Depends(require_scholar)]


async def _can_write(db: AsyncSession, user: User) -> bool:
    roles = await _roles(db, user)
    return SCHOLAR_ROLE in roles or allowed(roles, "islamic.edit")


class MeOut(BaseModel):
    scholar: bool
    can_edit: bool
    name_ar: str | None = None
    may_be_named: bool = False


async def _me(db: AsyncSession, user: User) -> MeOut:
    roles = await _roles(db, user)
    profile = await db.get(IslamicReviewer, user.id)
    return MeOut(
        scholar=SCHOLAR_ROLE in roles,
        can_edit=allowed(roles, "islamic.edit"),
        name_ar=profile.name_ar if profile else None,
        may_be_named=bool(profile and profile.may_be_named),
    )


# ---- rows ---------------------------------------------------------------------------------------------


def _unit(unit_id: str) -> Unit:
    unit = next((u for u in content_units() if u.id == unit_id), None)
    if unit is None:
        raise ApiError("not_found", 404)
    return unit


async def _row(db: AsyncSession, unit: Unit) -> IslamicUnitReview:
    row = await db.get(IslamicUnitReview, unit.id)
    if row is None:
        row = IslamicUnitReview(unit_id=unit.id, volume=unit.volume, status=S.draft)
        db.add(row)
        await db.flush()
    return row


async def _reviewer_name(db: AsyncSession, user: User) -> str:
    profile = await db.get(IslamicReviewer, user.id)
    return (profile.name_ar if profile and profile.name_ar.strip() else user.full_name).strip()


def _event(row: IslamicUnitReview, kind: str, user: User, name: str, **kw: Any) -> IslamicReviewEvent:
    return IslamicReviewEvent(unit_id=row.unit_id, kind=kind, author_user_id=user.id, author_name=name, **kw)


def _audit(user: User, action: str, unit_id: str, **data: Any) -> AuditLog:
    return AuditLog(
        actor_user_id=user.id, action=action, entity_type="islamic_unit", entity_id=unit_id, data=data
    )


# ---- the overview ---------------------------------------------------------------------------------------


class PreviewInfo(BaseModel):
    status: str  # none | queued | ready | failed
    run_id: str | None = None
    pages: int = 0
    rendered_at: datetime | None = None
    error: str | None = None
    problems: list[Any] = Field(default_factory=list)


class PointOut(BaseModel):
    source_id: str
    title_ar: str
    question: str
    decision: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None


class VolumeSummary(BaseModel):
    id: str
    name_ar: str
    title_ar: str
    units: int
    approved: int
    in_review: int
    changes_requested: int
    all_approved: bool
    previews: PreviewInfo


class OverviewOut(BaseModel):
    volumes: list[VolumeSummary]
    general_points: list[PointOut]  # questions no page cites (e.g. drawing people at all)
    me: MeOut


def _preview_info(row: IslamicReviewPreview | None) -> PreviewInfo:
    if row is None:
        return PreviewInfo(status="none")
    return PreviewInfo(
        status=row.status,
        run_id=row.run_id,
        pages=len(row.pages or []),
        rendered_at=row.rendered_at,
        error=row.error,
        problems=list(row.problems or []),
    )


def _point(sources: dict[str, dict[str, Any]], sid: str, state: ReviewState) -> PointOut:
    src, d = sources.get(sid, {}), state.decisions.get(sid)
    return PointOut(
        source_id=sid,
        title_ar=str(src.get("title_ar", sid)),
        question=str(src.get("scholar_decision", "")),
        decision=d.decision if d else None,
        decided_by=d.decided_by_name if d else None,
        decided_at=d.decided_at if d else None,
    )


@router.get("", dependencies=[Depends(require_permission("islamic.view"))])
async def overview(user: AdminUser, db: SessionDep) -> OverviewOut:
    p, state = plan(), await load_state(db)
    previews = {r.volume: r for r in (await db.execute(select(IslamicReviewPreview))).scalars()}
    grouped = units_by_volume(content_units())
    approved = state.approved_volumes()
    volumes = []
    for vid in VOLUMES:
        units = grouped.get(vid, [])
        if not units:
            continue
        statuses = [state.status(u.id) for u in units]
        volumes.append(
            VolumeSummary(
                id=vid,
                name_ar=VOLUME_NAMES_AR[vid],
                title_ar=str(p.volumes.get(vid, {}).get("title_ar", "")),
                units=len(units),
                approved=statuses.count(S.approved),
                in_review=statuses.count(S.scholar_review),
                changes_requested=statuses.count(S.changes_requested),
                all_approved=vid in approved,
                previews=_preview_info(previews.get(vid)),
            )
        )
    cited = {
        each
        for pages in p.pages.values()
        for pg in pages
        for s in pg.sources
        for each in _chain(p.sources, s)
    }
    general = [
        _point(p.sources, sid, state)
        for sid, src in p.sources.items()
        if src.get("scholar_decision") and sid not in cited
    ]
    return OverviewOut(volumes=volumes, general_points=general, me=await _me(db, user))


# ---- one volume -------------------------------------------------------------------------------------------


class PageOut(BaseModel):
    n: int
    kind: str
    type: str
    title: str
    sources: list[str]
    preview: str | None  # the PNG's admin link, once the volume's previews are rendered


class SourceOut(BaseModel):
    id: str
    kind: str
    title_ar: str
    status: str  # the register's status (proposed → … → scholar_approved), from sources.yaml
    question: str | None = None  # a `scholar_decision` point
    decision: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None


class EventOut(BaseModel):
    kind: str
    page: int | None
    source_id: str | None
    text: str
    author_name: str
    scholar: bool
    created_at: datetime


class UnitOut(BaseModel):
    id: str
    title_ar: str
    matter: bool
    status: ReviewStatus
    submitted_at: datetime | None
    reviewer_name: str | None
    decided_at: datetime | None
    approved_at: datetime | None
    preview_run: str | None
    pages: list[PageOut]
    sources: list[SourceOut]
    pending_points: int  # `scholar_decision` points without the scholar's answer: approval waits for them
    events: list[EventOut]


class VolumeOut(BaseModel):
    id: str
    name_ar: str
    title_ar: str
    all_approved: bool
    previews: PreviewInfo
    pages_mismatch: bool  # the rendered previews have another page count than the plan
    units: list[UnitOut]
    me: MeOut


def _check_volume(volume: str) -> str:
    if volume not in VOLUMES:
        raise ApiError("not_found", 404)
    return volume


@router.get("/volumes/{volume}", dependencies=[Depends(require_permission("islamic.view"))])
async def volume_detail(volume: str, user: AdminUser, db: SessionDep) -> VolumeOut:
    vid = _check_volume(volume)
    p, state = plan(), await load_state(db)
    units = units_by_volume(content_units()).get(vid, [])
    if not units:
        raise ApiError("not_found", 404)
    preview = await db.get(IslamicReviewPreview, vid)
    shots = list(preview.pages or []) if preview and preview.status == "ready" else []
    planned = p.pages.get(vid, [])
    events: dict[str, list[IslamicReviewEvent]] = {}
    rows = await db.execute(
        select(IslamicReviewEvent)
        .where(IslamicReviewEvent.unit_id.in_([u.id for u in units]))
        .order_by(IslamicReviewEvent.created_at)
    )
    for e in rows.scalars():
        events.setdefault(e.unit_id, []).append(e)

    def link(n: int) -> str | None:
        if not shots or n > len(shots) or preview is None:
            return None
        return f"/api/admin/islamic/review/previews/{vid}/{n}?run={preview.run_id}"

    out = []
    for u in units:
        pages = [pg for pg in planned if (pg.unit == u.id if not u.matter else pg.unit is None)]
        cited = list(dict.fromkeys(each for pg in pages for s in pg.sources for each in _chain(p.sources, s)))
        sources = []
        for sid in cited:
            src = p.sources.get(sid, {})
            point = _point(p.sources, sid, state) if src.get("scholar_decision") else None
            sources.append(
                SourceOut(
                    id=sid,
                    kind=str(src.get("kind", "")),
                    title_ar=str(src.get("title_ar", sid)),
                    status=str(src.get("status", "proposed")),
                    question=point.question if point else None,
                    decision=point.decision if point else None,
                    decided_by=point.decided_by if point else None,
                    decided_at=point.decided_at if point else None,
                )
            )
        row = state.rows.get(u.id)
        out.append(
            UnitOut(
                id=u.id,
                title_ar=u.title_ar,
                matter=u.matter,
                status=state.status(u.id),
                submitted_at=row.submitted_at if row else None,
                reviewer_name=row.reviewer_name if row else None,
                decided_at=row.decided_at if row else None,
                approved_at=row.approved_at if row else None,
                preview_run=row.preview_run if row else None,
                pages=[
                    PageOut(
                        n=pg.n,
                        kind=pg.kind,
                        type=pg.type,
                        title=pg.title,
                        sources=list(pg.sources),
                        preview=link(pg.n),
                    )
                    for pg in pages
                ],
                sources=sources,
                pending_points=sum(1 for s in sources if s.question and not s.decision),
                events=[
                    EventOut(
                        kind=e.kind,
                        page=e.page,
                        source_id=e.source_id,
                        text=e.text,
                        author_name=e.author_name,
                        scholar=e.scholar,
                        created_at=e.created_at,
                    )
                    for e in events.get(u.id, [])
                ],
            )
        )
    return VolumeOut(
        id=vid,
        name_ar=VOLUME_NAMES_AR[vid],
        title_ar=str(p.volumes.get(vid, {}).get("title_ar", "")),
        all_approved=vid in state.approved_volumes(),
        previews=_preview_info(preview),
        pages_mismatch=bool(shots) and len(shots) != len(planned),
        units=out,
        me=await _me(db, user),
    )


# ---- transitions --------------------------------------------------------------------------------------


class NoteIn(BaseModel):
    text: str = Field(default="", max_length=4000)
    page: int | None = Field(default=None, ge=0, le=400)
    source_id: str | None = Field(default=None, max_length=64)


class StatusOut(BaseModel):
    unit_id: str
    status: ReviewStatus
    volume_approved: bool


async def _status_out(db: AsyncSession, row: IslamicUnitReview) -> StatusOut:
    approved = (await load_state(db)).approved_volumes()
    return StatusOut(unit_id=row.unit_id, status=row.status, volume_approved=row.volume in approved)


@router.post("/units/{unit_id}/submit", dependencies=[Depends(require_permission("islamic.edit"))])
async def submit(unit_id: str, body: NoteIn, user: AdminUser, db: SessionDep) -> StatusOut:
    """Send a unit to the scholar: a draft, a unit the scholar sent back, or (with a note saying what changed)
    an approved unit whose pages were edited, which takes its volume off sale until it is approved again."""
    row = await _row(db, _unit(unit_id))
    reopen = row.status == S.approved
    if row.status == S.scholar_review:
        raise ApiError("review_transition", 409, {"from": row.status.value, "to": S.scholar_review.value})
    text = body.text.strip()
    if reopen and not text:
        raise ApiError("invalid_input", 422, {"fields": ["text"]})
    before = row.status
    row.status, row.submitted_at, row.submitted_by_user_id = S.scholar_review, datetime.now(UTC), user.id
    row.approved_at = None
    db.add(
        _event(row, "reopened" if reopen else "submitted", user, user.full_name, text=text, page=body.page)
    )
    db.add(_audit(user, "islamic.unit_submitted", row.unit_id, before=before.value, reopened=reopen))
    await db.commit()
    return await _status_out(db, row)


async def _volume_run(db: AsyncSession, volume: str) -> str | None:
    preview = await db.get(IslamicReviewPreview, volume)
    return preview.run_id if preview and preview.status == "ready" else None


@router.post("/units/{unit_id}/approve")
async def approve(unit_id: str, body: NoteIn, db: SessionDep, user: ScholarUser) -> StatusOut:
    """The scholar signs the unit off. Every `scholar_decision` point its pages cite needs an answer first."""
    unit = _unit(unit_id)
    row = await _row(db, unit)
    if row.status != S.scholar_review:
        raise ApiError("review_transition", 409, {"from": row.status.value, "to": S.approved.value})
    detail = await volume_detail(unit.volume, user, db)
    pending = next(u for u in detail.units if u.id == unit.id).pending_points
    if pending:
        raise ApiError("decisions_pending", 409, {"points": pending})
    now, name = datetime.now(UTC), await _reviewer_name(db, user)
    row.status, row.reviewer_user_id, row.reviewer_name = S.approved, user.id, name
    row.decided_at = row.approved_at = now
    row.preview_run = await _volume_run(db, unit.volume)
    db.add(_event(row, "approved", user, name, text=body.text.strip(), page=body.page, scholar=True))
    db.add(_audit(user, "islamic.unit_approved", row.unit_id, preview_run=row.preview_run))
    await db.commit()
    out = await _status_out(db, row)
    if out.volume_approved:
        db.add(
            AuditLog(
                actor_user_id=user.id,
                action="islamic.volume_approved",
                entity_type="islamic_volume",
                entity_id=unit.volume,
                data={"last_unit": unit.id},
            )
        )
        await db.commit()
    return out


@router.post("/units/{unit_id}/request-changes")
async def request_changes(unit_id: str, body: NoteIn, db: SessionDep, user: ScholarUser) -> StatusOut:
    """The scholar sends the unit back with what to change (also after approving it: the volume leaves the
    store until the unit is approved again)."""
    row = await _row(db, _unit(unit_id))
    if row.status not in (S.scholar_review, S.approved):
        raise ApiError("review_transition", 409, {"from": row.status.value, "to": S.changes_requested.value})
    text = body.text.strip()
    if not text:
        raise ApiError("invalid_input", 422, {"fields": ["text"]})
    now, name = datetime.now(UTC), await _reviewer_name(db, user)
    before = row.status
    row.status, row.reviewer_user_id, row.reviewer_name = S.changes_requested, user.id, name
    row.decided_at, row.approved_at = now, None
    row.preview_run = await _volume_run(db, row.volume)
    db.add(
        _event(
            row,
            "changes_requested",
            user,
            name,
            text=text,
            page=body.page,
            source_id=body.source_id,
            scholar=True,
        )
    )
    db.add(_audit(user, "islamic.unit_changes_requested", row.unit_id, before=before.value))
    await db.commit()
    return await _status_out(db, row)


class EventsOut(BaseModel):
    unit_id: str
    events: list[EventOut]


@router.post("/units/{unit_id}/notes", status_code=201)
async def add_note(unit_id: str, body: NoteIn, user: AdminUser, db: SessionDep) -> EventsOut:
    """A note on a unit, a page or a source, from the scholar or the staff writing the content."""
    if not await _can_write(db, user):
        raise ApiError("forbidden", 403)
    text = body.text.strip()
    if not text:
        raise ApiError("invalid_input", 422, {"fields": ["text"]})
    row = await _row(db, _unit(unit_id))
    scholar = SCHOLAR_ROLE in await _roles(db, user)
    name = await _reviewer_name(db, user) if scholar else user.full_name
    db.add(
        _event(row, "note", user, name, text=text, page=body.page, source_id=body.source_id, scholar=scholar)
    )
    await db.commit()
    rows = await db.execute(
        select(IslamicReviewEvent)
        .where(IslamicReviewEvent.unit_id == row.unit_id)
        .order_by(IslamicReviewEvent.created_at)
    )
    return EventsOut(
        unit_id=row.unit_id,
        events=[
            EventOut(
                kind=e.kind,
                page=e.page,
                source_id=e.source_id,
                text=e.text,
                author_name=e.author_name,
                scholar=e.scholar,
                created_at=e.created_at,
            )
            for e in rows.scalars()
        ],
    )


# ---- the scholar's points and details ------------------------------------------------------------------


class DecisionIn(BaseModel):
    decision: str = Field(min_length=1, max_length=4000)


@router.put("/decisions/{source_id}")
async def decide(source_id: str, body: DecisionIn, db: SessionDep, user: ScholarUser) -> PointOut:
    """The scholar's answer to a point where scholars differ or the age needs care (§3.4). The content follows
    it wherever the source is used; changing it later is allowed and logged."""
    src = plan().sources.get(source_id)
    if not src or not src.get("scholar_decision"):
        raise ApiError("not_found", 404)
    text = body.decision.strip()
    if not text:
        raise ApiError("invalid_input", 422, {"fields": ["decision"]})
    name = await _reviewer_name(db, user)
    row = await db.get(IslamicScholarDecision, source_id)
    before = row.decision if row else None
    if row is None:
        row = IslamicScholarDecision(source_id=source_id)
    row.question, row.decision = str(src["scholar_decision"]), text
    row.decided_by_user_id, row.decided_by_name, row.decided_at = user.id, name, datetime.now(UTC)
    db.add(row)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="islamic.scholar_decision",
            entity_type="islamic_source",
            entity_id=source_id,
            data={"changed": before is not None},
        )
    )
    await db.commit()
    return PointOut(
        source_id=source_id,
        title_ar=str(src.get("title_ar", source_id)),
        question=row.question,
        decision=row.decision,
        decided_by=row.decided_by_name,
        decided_at=row.decided_at,
    )


class ProfileIn(BaseModel):
    name_ar: str = Field(min_length=2, max_length=120)
    may_be_named: bool


@router.get("/me")
async def get_me(user: AdminUser, db: SessionDep) -> MeOut:
    return await _me(db, user)


@router.put("/me")
async def put_me(body: ProfileIn, db: SessionDep, user: ScholarUser) -> MeOut:
    """The scholar's name as it would be printed, and whether they agree to «راجعه علميًّا: …» in the book."""
    name = " ".join(body.name_ar.split())
    if len(name) < 2:
        raise ApiError("invalid_input", 422, {"fields": ["name_ar"]})
    profile = await db.get(IslamicReviewer, user.id)
    if profile is None:
        profile = IslamicReviewer(user_id=user.id, name_ar=name)
        db.add(profile)
    consented = body.may_be_named and not profile.may_be_named
    profile.name_ar, profile.may_be_named = name, body.may_be_named
    profile.named_consent_at = (
        datetime.now(UTC) if consented else (profile.named_consent_at if body.may_be_named else None)
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="islamic.reviewer_profile",
            entity_type="user",
            entity_id=str(user.id),
            data={"may_be_named": body.may_be_named},
        )
    )
    await db.commit()
    return await _me(db, user)


# ---- previews --------------------------------------------------------------------------------------------


@router.post(
    "/volumes/{volume}/previews", status_code=202, dependencies=[Depends(require_permission("islamic.edit"))]
)
async def render_previews(volume: str, user: AdminUser, db: SessionDep, queue: QueueDep) -> PreviewInfo:
    """Render the volume's pages for review (a sample child, no print checks): one PNG per page."""
    vid = _check_volume(volume)
    row = await db.get(IslamicReviewPreview, vid)
    now = datetime.now(UTC)
    if row is not None and row.status == "queued" and now - row.updated_at < PREVIEW_STALE:
        raise ApiError("previews_busy", 409)
    run = secrets.token_hex(8)
    if row is None:
        row = IslamicReviewPreview(volume=vid, run_id=run, status="queued", pages=[])
        db.add(row)
    row.run_id, row.status, row.error, row.requested_by_user_id = run, "queued", None, user.id
    row.updated_at = now
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="islamic.previews_requested",
            entity_type="islamic_volume",
            entity_id=vid,
            data={"run": run},
        )
    )
    await db.commit()
    enqueue(queue, PREVIEW_JOB, vid, run)
    return _preview_info(row)


@router.get("/previews/{volume}/{n}", dependencies=[Depends(require_permission("islamic.view"))])
async def preview_png(volume: str, n: int, db: SessionDep, storage: StorageDep) -> Response:
    row = await db.get(IslamicReviewPreview, _check_volume(volume))
    if row is None or row.status != "ready":
        raise ApiError("not_found", 404)
    pages = list(row.pages or [])
    key = row.cover_key if n == 0 else (pages[n - 1] if 0 < n <= len(pages) else None)
    if not key:
        raise ApiError("not_found", 404)
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


# ---- the export ----------------------------------------------------------------------------------------


@router.get("/export", dependencies=[Depends(require_permission("islamic.view"))])
async def export(db: SessionDep) -> dict[str, Any]:
    return build_export(await load_state(db))
