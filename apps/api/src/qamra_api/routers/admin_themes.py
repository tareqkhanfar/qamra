"""Admin: theme versions in the template studio (Addendum 4 §3.1, §3.3, §3.5).

- A theme's versions go draft → in_review → approved → live, with history and rollback (a retired version
  goes live again). One version per theme is open at a time, so edits never fork.
- The page editor's text edits land in the open draft, made from the live version when there is none.
- «ترجمة»: an English draft of a version's texts by the text model, only when an editor asks for it after
  seeing the estimate.
Every change is in the audit log. Books keep the definition they started with. Classic templates keep their
art, and their texts show as stale until an editor refreshes them (POST /api/admin/classic/.../texts).
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import Theme
from qamra_ai.pipeline.translate import estimate
from qamra_ai.pipeline.vowelize import with_current_texts
from qamra_api import runtime_settings
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.theme_versions import (
    display_titles,
    ensure_live,
    history,
    new_draft,
    open_version,
    problems,
    publish,
)
from qamra_core.db.classic import ClassicTemplate
from qamra_core.db.models import AuditLog, User
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.studio import ThemeVersion, ThemeVersionStatus

router = APIRouter(prefix="/api/admin/themes", tags=["admin"], dependencies=[Depends(require_admin)])

TRANSLATE_JOB = "qamra_worker.jobs.studio.translate_theme_version"
V = ThemeVersionStatus
MOVES: dict[ThemeVersionStatus, tuple[ThemeVersionStatus, ...]] = {
    V.draft: (V.in_review,),
    V.in_review: (V.approved, V.draft),
    V.approved: (V.in_review, V.draft),
}
TEXT_KEYS = ("title_ar", "title_en", "blurb_ar", "blurb_en")


class VersionOut(BaseModel):
    version: int
    status: str
    source: str
    base_version: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None  # a staff member's name
    submitted_at: datetime | None
    approved_at: datetime | None
    approved_by: str | None
    published_at: datetime | None
    published_by: str | None
    translate: dict[str, Any] | None


class ThemeOut(BaseModel):
    slug: str
    title_ar: str
    title_en: str
    live_version: int
    open: VersionOut | None
    versions: int
    templates: int
    stale_templates: int  # Classic templates whose texts differ from the live version's


class ThemeDetail(ThemeOut):
    history: list[VersionOut]


class PageText(BaseModel):
    index: int
    layout: str
    text_pos: str
    text_ar: str
    text_en: str


class Change(BaseModel):
    key: str  # "title_ar", "page:3:text_en", …
    before: str | None
    after: str | None


class VersionDetail(VersionOut):
    theme: str
    live_version: int
    title_ar: str
    title_en: str
    pages: list[PageText]
    changes: list[Change]  # against the live version


async def _names(db: AsyncSession, versions: list[ThemeVersion]) -> dict[uuid.UUID, str]:
    ids = {i for v in versions for i in (v.created_by_user_id, v.approved_by_user_id, v.published_by_user_id)}
    ids.discard(None)
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.full_name).where(User.id.in_(ids)))
    return {uid: name for uid, name in rows.all()}


def _version_out(v: ThemeVersion, names: dict[uuid.UUID, str]) -> VersionOut:
    def name(uid: uuid.UUID | None) -> str | None:
        return names.get(uid) if uid else None

    return VersionOut(
        version=v.version,
        status=v.status.value,
        source=v.source,
        base_version=v.base_version,
        note=v.note,
        created_at=v.created_at,
        updated_at=v.updated_at,
        created_by=name(v.created_by_user_id),
        submitted_at=v.submitted_at,
        approved_at=v.approved_at,
        approved_by=name(v.approved_by_user_id),
        published_at=v.published_at,
        published_by=name(v.published_by_user_id),
        translate=(v.meta or {}).get("translate"),
    )


def _texts(definition: dict[str, Any]) -> dict[str, str]:
    """Every text an editor can change, flat: title, blurb, lesson, questions and pages."""
    out = {k: str(definition.get(k) or "") for k in TEXT_KEYS}
    fp = definition.get("for_parents") or {}
    for lang in ("ar", "en"):
        out[f"lesson_{lang}"] = str(fp.get(f"lesson_{lang}") or "")
        for i, q in enumerate(fp.get(f"questions_{lang}") or []):
            out[f"question:{i + 1}:{lang}"] = str(q)
    for p in definition.get("pages") or []:
        for k in ("text_ar", "text_en"):
            out[f"page:{p.get('index')}:{k}"] = str(p.get(k) or "")
    return out


def changes(before: dict[str, Any], after: dict[str, Any]) -> list[Change]:
    old, new = _texts(before), _texts(after)
    keys = list(dict.fromkeys([*old, *new]))
    return [Change(key=k, before=old.get(k), after=new.get(k)) for k in keys if old.get(k) != new.get(k)]


async def _theme(db: AsyncSession, slug: str) -> ThemeRow:
    row = (await db.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one_or_none()
    if row is None:
        raise ApiError("not_found", 404)
    return row


async def _version(db: AsyncSession, row: ThemeRow, number: int) -> ThemeVersion:
    q = select(ThemeVersion).where(ThemeVersion.theme_id == row.id, ThemeVersion.version == number)
    v = (await db.execute(q)).scalar_one_or_none()
    if v is None:
        raise ApiError("not_found", 404)
    return v


def texts_stale(t: ClassicTemplate, live: dict[str, Any]) -> bool:
    """The live version's words differ from the template's (its art stays; a refresh takes the words)."""
    pinned = t.generation.get("theme_def") or {}
    return bool(pinned) and with_current_texts(pinned, live) != pinned


async def _theme_out(db: AsyncSession, row: ThemeRow, *, full: bool = False) -> ThemeDetail:
    versions = await history(db, row.id)
    names = await _names(db, versions)
    live = next((v for v in versions if v.status == V.live), None)
    open_ = next((v for v in versions if v.status in MOVES), None)
    templates = list(
        (await db.execute(select(ClassicTemplate).where(ClassicTemplate.theme_id == row.id))).scalars()
    )
    return ThemeDetail(
        slug=row.slug,
        title_ar=display_titles(row.definition)[0],
        title_en=display_titles(row.definition)[1],
        live_version=live.version if live else row.version,
        open=_version_out(open_, names) if open_ else None,
        versions=len(versions),
        templates=len(templates),
        stale_templates=sum(texts_stale(t, row.definition) for t in templates),
        history=[_version_out(v, names) for v in versions] if full else [],
    )


async def _detail(db: AsyncSession, row: ThemeRow, v: ThemeVersion) -> VersionDetail:
    theme = Theme.model_validate(v.definition)
    live = next((x for x in await history(db, row.id) if x.status == V.live), None)
    return VersionDetail(
        **_version_out(v, await _names(db, [v])).model_dump(),
        theme=row.slug,
        live_version=live.version if live else row.version,
        title_ar=theme.title_ar,
        title_en=theme.title_en,
        pages=[
            PageText(
                index=p.index, layout=p.layout, text_pos=p.text_pos, text_ar=p.text_ar, text_en=p.text_en
            )
            for p in theme.pages
        ],
        changes=changes(row.definition, v.definition),
    )


def _audit(admin: AdminUser, action: str, row: ThemeRow, **data: Any) -> AuditLog:
    return AuditLog(
        actor_user_id=admin.id,
        action=action,
        entity_type="theme",
        entity_id=str(row.id),
        data={"theme": row.slug, **data},
    )


# ---- reading --------------------------------------------------------------------------------------------


@router.get("", dependencies=[Depends(require_permission("themes.view"))])
async def list_themes(db: SessionDep) -> list[ThemeOut]:
    rows = (await db.execute(select(ThemeRow).order_by(ThemeRow.slug))).scalars().all()
    return [ThemeOut(**(await _theme_out(db, r)).model_dump(exclude={"history"})) for r in rows]


@router.get("/{slug}", dependencies=[Depends(require_permission("themes.view"))])
async def theme_detail(slug: str, db: SessionDep) -> ThemeDetail:
    return await _theme_out(db, await _theme(db, slug), full=True)


@router.get("/{slug}/versions/{version}", dependencies=[Depends(require_permission("themes.view"))])
async def version_detail(slug: str, version: int, db: SessionDep) -> VersionDetail:
    row = await _theme(db, slug)
    return await _detail(db, row, await _version(db, row, version))


# ---- editing ----------------------------------------------------------------------------------------------


class DraftIn(BaseModel):
    base: int | None = None  # copy this version (default: the live one)
    note: str | None = Field(default=None, max_length=300)


@router.post("/{slug}/versions", status_code=201, dependencies=[Depends(require_permission("themes"))])
async def create_draft(slug: str, body: DraftIn, admin: AdminUser, db: SessionDep) -> VersionDetail:
    row = await _theme(db, slug)
    if (current := await open_version(db, row.id)) is not None:
        raise ApiError("version_open", 409, {"version": current.version, "status": current.status.value})
    base = await _version(db, row, body.base) if body.base is not None else await ensure_live(db, row)
    draft = await new_draft(db, row, base, admin.id, body.note)
    db.add(_audit(admin, "theme.version_created", row, version=draft.version, base=base.version))
    await db.commit()
    return await _detail(db, row, draft)


class PageTextIn(BaseModel):
    text_ar: str | None = Field(default=None, min_length=1, max_length=800)
    text_en: str | None = Field(default=None, min_length=1, max_length=800)
    note: str | None = Field(default=None, max_length=300)


@router.put("/{slug}/pages/{index}/text", dependencies=[Depends(require_permission("themes"))])
async def edit_page_text(
    slug: str, index: int, body: PageTextIn, admin: AdminUser, db: SessionDep
) -> VersionDetail:
    """A page's words (m/f variants inside the Arabic, and the English) change in the open draft, made from
    the live version when the theme has none. A version in review or approved must go back to draft first."""
    row = await _theme(db, slug)
    draft = await open_version(db, row.id)
    if draft is not None and draft.status != V.draft:
        raise ApiError("version_pending", 409, {"version": draft.version, "status": draft.status.value})
    created = draft is None
    if draft is None:
        draft = await new_draft(db, row, await ensure_live(db, row), admin.id, body.note)
    definition = {**draft.definition, "pages": [dict(p) for p in draft.definition.get("pages") or []]}
    page = next((p for p in definition["pages"] if p.get("index") == index), None)
    if page is None:
        raise ApiError("not_found", 404)
    edits = {k: " ".join(v.split()) for k, v in (("text_ar", body.text_ar), ("text_en", body.text_en)) if v}
    fields = [k for k, v in edits.items() if page.get(k) != v]
    page.update(edits)
    found = problems(definition)
    if found:
        raise ApiError("theme_invalid", 422, {"problems": found})
    draft.definition = definition
    if body.note:
        draft.note = body.note
    db.add(_audit(admin, "theme.text_edited", row, version=draft.version, page=index, fields=fields,
                  created=created))  # fmt: skip
    await db.commit()
    return await _detail(db, row, draft)


class StatusIn(BaseModel):
    to: Literal["draft", "in_review", "approved"]


@router.post("/{slug}/versions/{version}/status", dependencies=[Depends(require_permission("themes"))])
async def change_status(
    slug: str, version: int, body: StatusIn, admin: AdminUser, db: SessionDep
) -> VersionDetail:
    """draft → in_review → approved (or back to draft). Publishing is its own step."""
    row = await _theme(db, slug)
    v = await _version(db, row, version)
    to = V(body.to)
    if to not in MOVES.get(v.status, ()):
        raise ApiError("invalid_transition", 409, {"from": v.status.value, "to": to.value})
    if to == V.approved and (found := problems(v.definition)):
        raise ApiError("theme_invalid", 422, {"problems": found})
    before, v.status = v.status, to
    now = datetime.now(UTC)
    if to == V.in_review:
        v.submitted_at = now
    if to == V.approved:
        v.approved_at, v.approved_by_user_id = now, admin.id
    db.add(_audit(admin, "theme.version_status", row, version=v.version, **{"from": before.value, "to": to}))
    await db.commit()
    return await _detail(db, row, v)


@router.post("/{slug}/versions/{version}/publish", dependencies=[Depends(require_permission("themes"))])
async def publish_version(slug: str, version: int, admin: AdminUser, db: SessionDep) -> VersionDetail:
    """An approved version becomes the live definition: new books use it; books already made keep theirs,
    and Classic templates keep their art (their texts show as stale until refreshed)."""
    return await _go_live(slug, version, admin, db, V.approved, "theme.version_published")


@router.post("/{slug}/versions/{version}/rollback", dependencies=[Depends(require_permission("themes"))])
async def rollback_version(slug: str, version: int, admin: AdminUser, db: SessionDep) -> VersionDetail:
    """A version that was live before goes live again."""
    return await _go_live(slug, version, admin, db, V.retired, "theme.version_rolled_back")


async def _go_live(
    slug: str, version: int, admin: AdminUser, db: AsyncSession, need: ThemeVersionStatus, action: str
) -> VersionDetail:
    row = await _theme(db, slug)
    v = await _version(db, row, version)
    if v.status != need:
        raise ApiError("invalid_transition", 409, {"from": v.status.value, "to": V.live.value})
    if found := problems(v.definition):
        raise ApiError("theme_invalid", 422, {"problems": found})
    replaced = await publish(db, row, v, admin.id)
    db.add(_audit(admin, action, row, version=v.version, replaced=replaced.version if replaced else None))
    await db.commit()
    return await _detail(db, row, v)


@router.delete(
    "/{slug}/versions/{version}", status_code=204, dependencies=[Depends(require_permission("themes"))]
)
async def discard_draft(slug: str, version: int, admin: AdminUser, db: SessionDep) -> None:
    row = await _theme(db, slug)
    v = await _version(db, row, version)
    if v.status != V.draft:
        raise ApiError("invalid_transition", 409, {"from": v.status.value, "to": "discarded"})
    await db.delete(v)
    db.add(_audit(admin, "theme.version_discarded", row, version=version))
    await db.commit()


# ---- «ترجمة»: an English draft by the text model --------------------------------------------------------


class TranslateEstimate(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    usd: float
    pages: int


async def _estimate(db: AsyncSession, settings: SettingsDep, v: ThemeVersion) -> TranslateEstimate:
    model = str((await runtime_settings.current(db, settings)).values["text_model"])
    theme = Theme.model_validate(v.definition)
    tokens_in, tokens_out, usd = estimate(theme, model)
    return TranslateEstimate(
        model=model, input_tokens=tokens_in, output_tokens=tokens_out, usd=usd, pages=len(theme.pages)
    )


@router.get("/{slug}/versions/{version}/translate", dependencies=[Depends(require_permission("themes"))])
async def translate_estimate(
    slug: str, version: int, db: SessionDep, settings: SettingsDep
) -> TranslateEstimate:
    """What the English draft would cost (no call is made)."""
    row = await _theme(db, slug)
    return await _estimate(db, settings, await _version(db, row, version))


class TranslateIn(BaseModel):
    confirm: Literal[True]  # the editor saw the estimate


@router.post(
    "/{slug}/versions/{version}/translate",
    status_code=202,
    dependencies=[Depends(require_permission("themes"))],
)
async def translate_version(
    slug: str,
    version: int,
    body: TranslateIn,
    admin: AdminUser,
    db: SessionDep,
    settings: SettingsDep,
    queue: QueueDep,
) -> VersionDetail:
    """The English texts of `version`, drafted by the text model into that version when it is the open
    draft, or else into a new draft copied from it. An editor reviews it like any other change."""
    row = await _theme(db, slug)
    v = await _version(db, row, version)
    current = await open_version(db, row.id)
    if current is not None and current.id != v.id:
        raise ApiError("version_open", 409, {"version": current.version, "status": current.status.value})
    if current is not None and current.status != V.draft:
        raise ApiError("version_pending", 409, {"version": current.version, "status": current.status.value})
    if ((v.meta or {}).get("translate") or {}).get("state") in ("queued", "running"):
        raise ApiError("busy", 409)
    cost = await _estimate(db, settings, v)
    target = v if v.status == V.draft else await new_draft(db, row, v, admin.id)
    state = {
        "state": "queued",
        "estimate_usd": cost.usd,
        "model": cost.model,
        "at": datetime.now(UTC).isoformat(),
    }
    target.meta = {**(target.meta or {}), "translate": state}
    db.add(_audit(admin, "theme.translate_requested", row, version=target.version, estimate_usd=cost.usd))
    await db.commit()
    enqueue(queue, TRANSLATE_JOB, str(target.id))
    return await _detail(db, row, target)
