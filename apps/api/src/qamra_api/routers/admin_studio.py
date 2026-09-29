"""Admin: the template studio's Classic templates and their bulk actions (Addendum 4 §3.2, §3.4, §3.5).

- Every template per theme × art style × look, with its status, pages drawn, flags, one-time cost, whether
  its Arabic is vowelized, and whether its texts are stale (the theme's live words changed since).
- Bulk: copy templates' settings to another art style as drafts (drawn only when an editor clicks generate),
  publish or take several off sale, and schedule a go-live date (qamra_worker.jobs.studio, every 5 minutes).
- The page editor's words: each page's text in the template, and in the theme version being edited.
Nothing here calls an AI model. Every change is in the audit log.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import Theme
from qamra_api.deps import AdminUser, SessionDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_api.routers.admin_classic import texts_ready
from qamra_api.routers.admin_themes import texts_stale
from qamra_api.theme_versions import display_titles, open_version
from qamra_core.db.classic import ClassicTemplate, ClassicTemplatePage, TemplateJob, TemplateStatus
from qamra_core.db.models import AuditLog
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.store import ArtStyle

router = APIRouter(prefix="/api/admin/studio", tags=["admin"], dependencies=[Depends(require_admin)])

S = TemplateStatus
VARIANTS = ("girl", "girl_hijab", "boy")
BUSY = (TemplateJob.queued, TemplateJob.running)


class StudioTemplate(BaseModel):
    id: uuid.UUID
    theme: str
    theme_title_ar: str
    theme_title_en: str
    style: str
    variant: str
    status: str
    job: str
    theme_version: int  # the version whose words the template has
    live_version: int
    pages_drawn: int
    pages_total: int
    flags: list[str]
    cost_usd: float
    vowelized: bool
    texts_stale: bool
    story_changed: bool  # the live story's pages no longer line up: a new template is needed
    publish_at: datetime | None
    live_at: datetime | None
    updated_at: datetime


class Option(BaseModel):
    slug: str
    title_ar: str
    title_en: str


class StudioList(BaseModel):
    templates: list[StudioTemplate]
    themes: list[Option]
    styles: list[Option]
    variants: list[str]


def _indices(definition: dict[str, Any]) -> list[Any]:
    return [p.get("index") for p in definition.get("pages") or []]


def _row(t: ClassicTemplate, theme: ThemeRow, drawn: int) -> StudioTemplate:
    pinned = t.generation.get("theme_def") or {}
    return StudioTemplate(
        id=t.id,
        theme=theme.slug,
        theme_title_ar=display_titles(theme.definition)[0],
        theme_title_en=display_titles(theme.definition)[1],
        style=t.art_style,
        variant=t.variant,
        status=t.status.value,
        job=t.job.value,
        theme_version=t.theme_version,
        live_version=theme.version,
        pages_drawn=drawn,
        pages_total=1 + len(pinned.get("pages") or []),
        flags=list(t.flags or []),
        cost_usd=float(t.cost_usd or 0),
        vowelized=texts_ready(t),
        texts_stale=texts_stale(t, theme.definition),
        story_changed=bool(pinned) and _indices(pinned) != _indices(theme.definition),
        publish_at=t.publish_at,
        live_at=t.live_at,
        updated_at=t.updated_at,
    )


@router.get("/templates", dependencies=[Depends(require_permission("templates.view"))])
async def list_templates(
    db: SessionDep, theme: str | None = None, status: TemplateStatus | None = None, style: str | None = None
) -> StudioList:
    q = select(ClassicTemplate, ThemeRow).join(ThemeRow, ThemeRow.id == ClassicTemplate.theme_id)
    if theme:
        q = q.where(ThemeRow.slug == theme)
    if status:
        q = q.where(ClassicTemplate.status == status)
    if style:
        q = q.where(ClassicTemplate.art_style == style)
    q = q.order_by(ThemeRow.slug, ClassicTemplate.art_style, ClassicTemplate.variant)
    rows = (await db.execute(q)).all()
    counts = select(ClassicTemplatePage.template_id, func.count()).where(
        ClassicTemplatePage.image_key.is_not(None)
    )
    grouped = await db.execute(counts.group_by(ClassicTemplatePage.template_id))
    drawn: dict[uuid.UUID, int] = {tid: n for tid, n in grouped.all()}
    themes = (await db.execute(select(ThemeRow).order_by(ThemeRow.slug))).scalars().all()
    styles = (
        await db.execute(select(ArtStyle).where(ArtStyle.active).order_by(ArtStyle.sort, ArtStyle.slug))
    ).scalars()
    return StudioList(
        templates=[_row(t, th, drawn.get(t.id, 0)) for t, th in rows],
        themes=[
            Option(
                slug=r.slug,
                title_ar=display_titles(r.definition)[0],
                title_en=display_titles(r.definition)[1],
            )
            for r in themes
            if Theme.model_validate(r.definition).available
        ],
        styles=[Option(slug=s.slug, title_ar=s.name_ar, title_en=s.name_en) for s in styles],
        variants=list(VARIANTS),
    )


def _audit(admin: AdminUser, action: str, t: ClassicTemplate, **data: Any) -> AuditLog:
    return AuditLog(
        actor_user_id=admin.id, action=action, entity_type="classic_template", entity_id=str(t.id), data=data
    )


class BulkOut(BaseModel):
    done: list[uuid.UUID]  # for a copy: the new drafts
    skipped: list[dict[str, str]]  # {"id", "reason"}


async def _templates(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, ClassicTemplate]:
    rows = (await db.execute(select(ClassicTemplate).where(ClassicTemplate.id.in_(ids)))).scalars()
    return {t.id: t for t in rows}


class CopyIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    style: str = Field(min_length=1, max_length=40)


@router.post("/templates/copy", dependencies=[Depends(require_permission("templates"))])
async def copy_to_style(body: CopyIn, admin: AdminUser, db: SessionDep) -> BulkOut:
    """Each template's settings (theme, look, language, budget) → a draft in another art style, with the
    theme's live story. Nothing is drawn until an editor clicks generate on the new draft."""
    style = (await db.execute(select(ArtStyle).where(ArtStyle.slug == body.style))).scalar_one_or_none()
    if style is None or not style.active:
        raise ApiError("invalid_style", 422)
    found = await _templates(db, body.ids)
    out = BulkOut(done=[], skipped=[])
    for tid in dict.fromkeys(body.ids):
        t = found.get(tid)
        reason = "not_found" if t is None else "same_style" if t.art_style == body.style else None
        if t is not None and reason is None:
            clash = select(ClassicTemplate.id).where(
                ClassicTemplate.theme_id == t.theme_id,
                ClassicTemplate.art_style == body.style,
                ClassicTemplate.variant == t.variant,
            )
            reason = "exists" if (await db.execute(clash)).first() else None
        theme = await db.get(ThemeRow, t.theme_id) if t is not None and reason is None else None
        if t is None or theme is None or reason is not None:
            out.skipped.append({"id": str(tid), "reason": reason or "not_found"})
            continue
        new = ClassicTemplate(
            theme_id=t.theme_id,
            theme_version=theme.version,
            art_style=body.style,
            variant=t.variant,
            lang=t.lang,
            source="generated",
            budget_usd=t.budget_usd,
            generation={
                "theme_def": theme.definition,
                "offline": t.generation.get("offline") or False,
                "copied_from": str(t.id),
            },
            created_by_user_id=admin.id,
        )
        db.add(new)
        await db.flush()
        db.add(_audit(admin, "classic.template_copied", new, source=str(t.id), style=body.style))
        out.done.append(new.id)
    await db.commit()
    return out


class PublishIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    to: Literal["live", "approved"] = "live"  # publish, or take off sale (back to approved)


@router.post("/templates/publish", dependencies=[Depends(require_permission("templates"))])
async def publish_many(body: PublishIn, admin: AdminUser, db: SessionDep) -> BulkOut:
    """Approved → live (or live → approved) for several templates; the others are skipped with a reason."""
    to = S(body.to)
    need = S.approved if to == S.live else S.live
    found = await _templates(db, body.ids)
    out = BulkOut(done=[], skipped=[])
    now = datetime.now(UTC)
    for tid in dict.fromkeys(body.ids):
        t = found.get(tid)
        reason = "not_found" if t is None else f"status:{t.status.value}" if t.status != need else None
        if t is not None and reason is None and t.job in BUSY:
            reason = "busy"
        if t is None or reason is not None:
            out.skipped.append({"id": str(tid), "reason": reason or "not_found"})
            continue
        t.status, t.publish_at = to, None
        if to == S.live:
            t.live_at = now
        db.add(_audit(admin, "classic.template_status", t, bulk=True, **{"from": need.value, "to": to.value}))
        out.done.append(t.id)
    await db.commit()
    return out


class ScheduleIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    publish_at: datetime | None  # None clears the schedule


@router.post("/templates/schedule", dependencies=[Depends(require_permission("templates"))])
async def schedule_many(body: ScheduleIn, admin: AdminUser, db: SessionDep) -> BulkOut:
    """An approved template goes live on its date (checked every few minutes); None clears the date."""
    when = body.publish_at
    if when is not None:
        when = when if when.tzinfo else when.replace(tzinfo=UTC)
        if when <= datetime.now(UTC):
            raise ApiError("schedule_invalid", 422)
    found = await _templates(db, body.ids)
    out = BulkOut(done=[], skipped=[])
    for tid in dict.fromkeys(body.ids):
        t = found.get(tid)
        reason = "not_found" if t is None else None
        if t is not None and when is not None and t.status != S.approved:
            reason = f"status:{t.status.value}"
        if t is None or reason is not None:
            out.skipped.append({"id": str(tid), "reason": reason or "not_found"})
            continue
        t.publish_at = when
        db.add(_audit(admin, "classic.template_scheduled", t, publish_at=when.isoformat() if when else None))
        out.done.append(t.id)
    await db.commit()
    return out


# ---- the page editor's words ------------------------------------------------------------------------------

TEXT_PT = {"young": (20.0, 18.0), "older": (16.0, 15.0)}  # qamra_pdf BookSpec: ages ≤ 5 / 6–8 (size, min)
SAMPLE = {"m": ("يوسف", "Yousef"), "f": ("ليان", "Layan")}


class Words(BaseModel):
    ar: str
    en: str


class TextPage(BaseModel):
    beat: int  # 0: the cover (its words are the title)
    layout: str | None
    area: str | None  # the text panel: top | bottom | left | right | top-right …; None: under the picture
    pinned: Words  # the template's words: what its books print now
    current: Words  # in the theme's open version (else the live one): what an editor changes
    vowelized: str | None  # the template's vowelized Arabic for its look, when ready


class TemplateTexts(BaseModel):
    template: uuid.UUID
    theme: str
    theme_title: Words  # the catalog name, for the editor's heading
    style: str
    style_title: Words
    variant: str
    gender: Literal["m", "f"]
    pinned_version: int
    live_version: int
    editing: dict[str, Any] | None  # the theme's open version: {"version", "status"}
    texts_stale: bool
    story_changed: bool
    vowelized: bool
    text_pt: dict[str, tuple[float, float]]
    sample: dict[str, str]  # name_ar, name_en, companion_ar, companion_en
    pages: list[TextPage]


def _words(definition: dict[str, Any]) -> dict[int, Words]:
    out = {0: Words(ar=str(definition.get("title_ar") or ""), en=str(definition.get("title_en") or ""))}
    for p in definition.get("pages") or []:
        out[int(p.get("index", 0))] = Words(ar=str(p.get("text_ar") or ""), en=str(p.get("text_en") or ""))
    return out


@router.get("/templates/{template_id}/texts", dependencies=[Depends(require_permission("templates.view"))])
async def template_texts(template_id: uuid.UUID, db: SessionDep) -> TemplateTexts:
    t = await db.get(ClassicTemplate, template_id)
    theme = await db.get(ThemeRow, t.theme_id) if t is not None else None
    if t is None or theme is None:
        raise ApiError("not_found", 404)
    open_ = await open_version(db, theme.id)
    pinned_def = t.generation.get("theme_def") or theme.definition
    pinned, current = _words(pinned_def), _words(open_.definition if open_ else theme.definition)
    gender: Literal["m", "f"] = "m" if t.variant == "boy" else "f"
    cache = (t.generation.get("texts") or {}).get("texts") or {}
    ready = texts_ready(t)
    vowelized = {int(p["index"]): str(p["text"]) for p in cache.get("pages") or []} if ready else {}
    if ready and cache.get("title"):
        vowelized[0] = str(cache["title"])
    rows = (
        await db.execute(
            select(ClassicTemplatePage)
            .where(ClassicTemplatePage.template_id == t.id)
            .order_by(ClassicTemplatePage.beat)
        )
    ).scalars()
    layouts = {p.beat: (p.layout, (p.text_box or {}).get("area")) for p in rows}
    parsed = Theme.model_validate(pinned_def)
    sample = parsed.catalog.sample_child if parsed.catalog else None
    name_ar, name_en = (
        (sample.name_ar, sample.name_en) if sample and sample.gender == gender else SAMPLE[gender]
    )
    companion = parsed.default_companion
    style = (await db.execute(select(ArtStyle).where(ArtStyle.slug == t.art_style))).scalar_one_or_none()
    theme_ar, theme_en = display_titles(theme.definition)
    beats = sorted(pinned)
    return TemplateTexts(
        template=t.id,
        theme=theme.slug,
        theme_title=Words(ar=theme_ar, en=theme_en),
        style=t.art_style,
        style_title=Words(ar=style.name_ar, en=style.name_en)
        if style
        else Words(ar=t.art_style, en=t.art_style),
        variant=t.variant,
        gender=gender,
        pinned_version=t.theme_version,
        live_version=theme.version,
        editing={"version": open_.version, "status": open_.status.value} if open_ else None,
        texts_stale=texts_stale(t, theme.definition),
        story_changed=_indices(pinned_def) != _indices(theme.definition),
        vowelized=ready,
        text_pt=TEXT_PT,
        sample={
            "name_ar": name_ar,
            "name_en": name_en,
            "companion_ar": companion.name_ar if companion else "",
            "companion_en": companion.name_en if companion else "",
        },
        pages=[
            TextPage(
                beat=b,
                layout=layouts.get(b, (None, None))[0] or ("cover" if b == 0 else None),
                area=layouts.get(b, (None, None))[1],
                pinned=pinned[b],
                current=current.get(b, pinned[b]),
                vowelized=vowelized.get(b),
            )
            for b in beats
        ],
    )
