from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_event import AuditEvent

async def log_action(
    db: AsyncSession,
    action: str,
    action_category: str,
    result: str,
    user_id: str | None = None,
    target_id: str | None = None,
    target_type: str | None = None,
    ip_address: str | None = None,
    workspace_id: str = "00000000-0000-0000-0000-000000000000",
    details: str | None = None
):
    """
    Helper to log security and system events to the audit_events table.
    """
    event = AuditEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        action_category=action_category,
        action=action,
        target_id=target_id,
        target_type=target_type,
        ip_address=ip_address,
        status=result,
        details=details
    )
    db.add(event)
    await db.commit()
