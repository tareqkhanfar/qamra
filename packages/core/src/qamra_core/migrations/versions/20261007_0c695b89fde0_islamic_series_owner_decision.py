"""«قلبي يعرف الله»: the owner's decision of 2026-10-07 opens the six volumes for sale.

Revision ID: 0c695b89fde0
Revises: e5dd2afbd62c
Create Date: 2026-10-07

The owner went through every page of V1–V5 and R himself (the notes he left were applied in ef3548f) and
decided on 2026-10-07 to sell the series on that review, for this release, instead of waiting for the
scholar's sign-off. See docs/decisions.md (2026-10-07).

- Every review unit of V1–V5 and R (`UNITS`: the units of content/islamic/units.yaml plus each volume's
  front and back matter, the ids `qamra_core.islamic_review.content_units` gives) becomes `approved`, with
  `approved_at`/`decided_at` now. No reviewer is named: `reviewer_name` and `reviewer_user_id` stay NULL,
  so the review export never gives a name and the books print no «راجعه علميًّا» line.
- One `islamic_review_events` row per unit (kind `approved`, `scholar` false, no author) carries `NOTE`: the
  unit's history shows the decision on the review page. Idempotent: a unit that already has the note gets no
  second one. (No `audit_logs` row: migrations leave that table to the app.)
- `islamic_scholar_decisions` is not touched: the store's gate does not read it (the open `scholar_decision`
  points stay open in the review workflow, kept for later use).
- The product's description loses the sentence that a scholar reviews every volume (only where the row still
  holds the seeded text; an admin's edit is left alone), and its `scholar_review` feature flag is dropped.
  Nothing replaces them.

Downgrade: those units go back to `draft` (decision fields cleared), only the rows this migration added are
deleted, and the description gets its sentence back.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "0c695b89fde0"
down_revision: str | None = "e5dd2afbd62c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNITS: dict[str, tuple[str, ...]] = {
    "V1": (
        "u-allah",
        "u-blessings",
        "u-prophet",
        "u-follow",
        "u-house",
        "u-myday1",
        "u-adhkar1",
        "u-manners1",
        "matter-v1",
    ),
    "V2": (
        "u-why-pray",
        "u-wudu",
        "u-prayer",
        "u-quran1",
        "u-surahs1",
        "u-adhkar2",
        "u-family1",
        "u-whatif1",
        "matter-v2",
    ),
    "V3": ("u-shahada", "u-prayer2", "u-zakat", "u-fasting", "u-hajj", "u-iman1", "u-iman2", "matter-v3"),
    "V4": ("u-adam", "u-nuh", "u-ibrahim", "u-yusuf", "u-musa", "u-yunus", "u-sira", "matter-v4"),
    "V5": ("u-manners2", "u-adab", "u-family2", "u-halal", "u-whatif2", "u-surahs2", "u-myday2", "matter-v5"),
    "R": ("u-ram1", "u-ram2", "u-ram3", "u-ram4", "u-eid1", "u-eid2", "matter-r"),
}
NOTE = (
    "owner decision 2026-10-07: approved for sale on the owner's own page-by-page review of the volume "
    "(2026-10-03..07), for this release, in place of the scholar's sign-off (docs/decisions.md)."
)
AUTHOR = "—"  # no reviewer is named anywhere

PRODUCT = "islamic-series"
# (column, seeded text, text now): the sentence about a scholar's review is removed, nothing replaces it
DESCRIPTIONS: list[tuple[str, str, str]] = [
    (
        "description_ar",
        "رحلة يتعرّف فيها طفلكم إلى الله ونبيّه ﷺ، ويعيش دينه في يومه بالقصة واللعب والأنشطة، باسمه وشخصيته. "
        "كل مجلد يراجعه مشرف علمي قبل طباعته.",
        "رحلة يتعرّف فيها طفلكم إلى الله ونبيّه ﷺ، ويعيش دينه في يومه بالقصة واللعب والأنشطة، باسمه وشخصيته.",
    ),
    (
        "description_en",
        "A journey in which your child comes to know Allah and His Prophet ﷺ and lives their faith every day, "
        "through stories, play and activities, with their own name and character. "
        "A scholar reviews every volume before it is printed.",
        "A journey in which your child comes to know Allah and His Prophet ﷺ and lives their faith every day, "
        "through stories, play and activities, with their own name and character.",
    ),
]

reviews = sa.table(
    "islamic_unit_reviews",
    sa.column("unit_id", sa.String),
    sa.column("volume", sa.String),
    sa.column("status", sa.String),
    sa.column("reviewer_user_id", sa.Uuid),
    sa.column("reviewer_name", sa.String),
    sa.column("decided_at", sa.DateTime(timezone=True)),
    sa.column("approved_at", sa.DateTime(timezone=True)),
    sa.column("preview_run", sa.String),
)
events = sa.table(
    "islamic_review_events",
    sa.column("id", sa.Uuid),
    sa.column("unit_id", sa.String),
    sa.column("kind", sa.String),
    sa.column("text", sa.Text),
    sa.column("author_user_id", sa.Uuid),
    sa.column("author_name", sa.String),
    sa.column("scholar", sa.Boolean),
)
products = sa.table(
    "products",
    sa.column("slug", sa.String),
    sa.column("description_ar", sa.Text),
    sa.column("description_en", sa.Text),
)


def unit_ids() -> list[str]:
    return [u for us in UNITS.values() for u in us]


def approve(conn: Connection) -> None:
    """Every unit approved under the owner's decision, with its note (once)."""
    now = sa.func.now()
    have: set[str] = set(
        conn.execute(sa.select(reviews.c.unit_id).where(reviews.c.unit_id.in_(unit_ids()))).scalars()
    )
    noted: set[str] = set(
        conn.execute(
            sa.select(events.c.unit_id).where(events.c.unit_id.in_(unit_ids()), events.c.text == NOTE)
        ).scalars()
    )
    for volume, ids in UNITS.items():
        for unit in ids:
            values = {
                "status": "approved",
                "reviewer_user_id": None,
                "reviewer_name": None,
                "decided_at": now,
                "approved_at": now,
                "preview_run": None,
            }
            if unit in have:
                if unit not in noted:  # a second run leaves the first decision's dates alone
                    conn.execute(reviews.update().where(reviews.c.unit_id == unit).values(values))
            else:
                conn.execute(reviews.insert().values(unit_id=unit, volume=volume, **values))
            if unit not in noted:
                conn.execute(
                    events.insert().values(
                        id=uuid.uuid4(),
                        unit_id=unit,
                        kind="approved",
                        text=NOTE,
                        author_user_id=None,
                        author_name=AUTHOR,
                        scholar=False,
                    )
                )


def revert(conn: Connection) -> None:
    """The units back to draft; only this migration's rows are deleted."""
    ids = unit_ids()
    conn.execute(events.delete().where(events.c.unit_id.in_(ids), events.c.text == NOTE))
    conn.execute(
        reviews.update()
        .where(reviews.c.unit_id.in_(ids))
        .values(
            status="draft",
            reviewer_user_id=None,
            reviewer_name=None,
            decided_at=None,
            approved_at=None,
            preview_run=None,
        )
    )


def descriptions(conn: Connection, forward: bool) -> None:
    for column, seeded, now in DESCRIPTIONS:
        frm, to = (seeded, now) if forward else (now, seeded)
        conn.execute(
            products.update()
            .where(products.c.slug == PRODUCT, products.c[column] == frm)
            .values({column: to})
        )
    if forward:  # the product's `scholar_review` feature flag (in the public catalog JSON) goes too
        conn.execute(
            sa.text(
                "UPDATE products SET features = features - 'scholar_review' "
                "WHERE slug = :slug AND features ? 'scholar_review'"
            ),
            {"slug": PRODUCT},
        )
    else:
        conn.execute(
            sa.text(
                "UPDATE products SET features = features || '{\"scholar_review\": true}'::jsonb "
                "WHERE slug = :slug AND NOT features ? 'scholar_review'"
            ),
            {"slug": PRODUCT},
        )


def upgrade() -> None:
    conn = op.get_bind()
    approve(conn)
    descriptions(conn, forward=True)


def downgrade() -> None:
    conn = op.get_bind()
    descriptions(conn, forward=False)
    revert(conn)
