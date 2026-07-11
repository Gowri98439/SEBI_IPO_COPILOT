from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_event import AuditEvent

async def log_audit_event(
    db: AsyncSession,
    workspace_id: str,
    action: str,
    user_id: str | None = None,
    target_id: str | None = None,
    target_type: str | None = None,
    status: str = "success",
    details: str | None = None,
):
    """
    Log an event to the immutable audit timeline.
    """
    event = AuditEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        target_id=target_id,
        target_type=target_type,
        status=status,
        details=details,
    )
    db.add(event)
    await db.commit()
