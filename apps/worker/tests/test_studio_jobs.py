"""The template studio's jobs: scheduled go-lives (cron) and the English draft of a theme version (fake text
model: no paid call)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.classic import ClassicTemplate, TemplateJob, TemplateStatus
from qamra_core.db.models import AuditLog, GenerationCost
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.studio import ThemeVersion, ThemeVersionStatus
from qamra_worker.jobs import studio
from qamra_worker.jobs.studio import publish_due, run_translation


def _theme(db: Session, slug: str = "first-day") -> ThemeRow:
    raw = yaml.safe_load((CONTENT_DIR / f"themes/{slug}/theme.yaml").read_text(encoding="utf-8"))
    row = ThemeRow(slug=slug, version=raw["version"], title_ar="t", title_en="t", age_min=3, age_max=7,
                   companion_slot=True, definition=raw)  # fmt: skip
    db.add(row)
    db.flush()
    return row


def _template(
    db: Session, theme: ThemeRow, variant: str, status: TemplateStatus, **kw: Any
) -> ClassicTemplate:
    t = ClassicTemplate(theme_id=theme.id, theme_version=theme.version, art_style="watercolor",
                        variant=variant, status=status, generation={"theme_def": theme.definition},
                        **kw)  # fmt: skip
    db.add(t)
    db.flush()
    return t


def test_scheduled_templates_go_live_on_their_date(db: Session) -> None:
    theme = _theme(db)
    now = datetime.now(UTC)
    due = _template(db, theme, "girl", TemplateStatus.approved, publish_at=now - timedelta(minutes=1))
    later = _template(db, theme, "boy", TemplateStatus.approved, publish_at=now + timedelta(days=1))
    missed = _template(db, theme, "girl_hijab", TemplateStatus.in_review, publish_at=now - timedelta(hours=1))
    db.commit()
    out = publish_due(db, now)
    assert out == {"published": [str(due.id)], "missed": [str(missed.id)]}
    assert due.status == TemplateStatus.live and due.live_at == now and due.publish_at is None
    assert later.status == TemplateStatus.approved and later.publish_at is not None
    assert missed.status == TemplateStatus.in_review and missed.publish_at is None
    logged = {a.entity_id: a for a in db.execute(select(AuditLog)).scalars()}
    assert logged[str(due.id)].data["to"] == "live" and logged[str(due.id)].actor_user_id is None
    assert logged[str(missed.id)].action == "classic.template_schedule_missed"
    later.publish_at, later.job = now - timedelta(seconds=1), TemplateJob.running
    db.commit()
    assert publish_due(db, now) == {"published": [], "missed": []}  # busy drawing: the next run tries again
    assert later.publish_at is not None


def _draft(db: Session) -> ThemeVersion:
    theme = _theme(db)
    v = ThemeVersion(theme_id=theme.id, version=4, status=ThemeVersionStatus.draft, source="studio",
                     base_version=3, definition={**theme.definition, "version": 4}, meta={})  # fmt: skip
    db.add(v)
    db.commit()
    return v


@pytest.fixture
def fake_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    def make(settings: Any) -> Runtime:
        return Runtime(settings=settings, text=default_fake_text_provider(), image=FakeImageProvider())

    monkeypatch.setattr(studio, "make_runtime", make)


def test_the_english_draft_replaces_only_the_english(db: Session, fake_runtime: None) -> None:
    v = _draft(db)
    arabic = [p["text_ar"] for p in v.definition["pages"]]
    assert run_translation(db, v) == {"status": "done", "cost_usd": 0.0}
    db.refresh(v)
    pages = v.definition["pages"]
    assert [p["text_ar"] for p in pages] == arabic
    assert pages[0]["text_en"] == "{name} on page 1." and v.definition["title_en"] == "{name}'s story"
    assert v.definition["for_parents"]["questions_en"] == ["Question 1?", "Question 2?"]
    assert v.meta["translate"]["state"] == "done" and v.meta["translate"]["cost_usd"] == 0.0
    cost = db.execute(select(GenerationCost)).scalars().one()
    assert cost.step == "translate:first-day:v4" and cost.book_id is None
    action = db.execute(select(AuditLog.action)).scalars().one()
    assert action == "theme.version_translated"


def test_a_translation_for_a_version_no_longer_a_draft_is_not_saved(db: Session, fake_runtime: None) -> None:
    v = _draft(db)
    v.status = ThemeVersionStatus.in_review
    db.commit()
    with pytest.raises(ValueError, match="no longer a draft"):
        run_translation(db, v)
    db.rollback()
    db.refresh(v)
    assert v.definition["pages"][0]["text_en"] != "{name} on page 1."
    assert db.execute(select(GenerationCost)).scalars().one().usd == 0  # the call's cost is still logged
