"""The guardian's consent (CLAUDE.md §3.1), shared by the parent create flow and the kindergarten invite link:
one versioned record per acceptance, with when and from where, before any photo is uploaded."""

import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import AuditLog, Consent


def record_consent(
    db: AsyncSession,
    request: Request,
    *,
    user_id: uuid.UUID,
    child_id: uuid.UUID,
    version: str,
    scope: str = "photo_processing",
) -> None:
    """Adds the consent and its audit entry to the session (the caller commits)."""
    db.add(
        Consent(
            child_id=child_id,
            guardian_user_id=user_id,
            consent_text_version=version,
            scope=scope,
            ip=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=user_id,
            action="consent.given",
            entity_type="child",
            entity_id=str(child_id),
            data={"version": version, "scope": scope},
        )
    )
