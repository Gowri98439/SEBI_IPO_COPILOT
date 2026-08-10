"""
Immutable Audit Trail Logger
Records every significant state change, AI action, and user decision.
"""
from __future__ import annotations

import logging
import json
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditLogger:
    
    @staticmethod
    async def log_event(
        db: AsyncSession,
        workspace_id: str,
        action: str,
        action_category: str = "DOCUMENT",
        user: Optional[User] = None,
        target_id: Optional[str] = None,
        target_type: Optional[str] = None,
        previous_state: Optional[Any] = None,
        new_state: Optional[Any] = None,
        reason: Optional[str] = None,
        evidence_id: Optional[str] = None,
        ai_model: Optional[str] = None,
        prompt_version: Optional[str] = None,
        regulation_version: Optional[str] = None,
        ip_address: Optional[str] = None,
        status: str = "success"
    ) -> AuditEvent:
        """
        Create a new Immutable Audit Trail event.
        """
        # Convert state dictionaries to JSON string
        prev_str = json.dumps(previous_state) if previous_state else None
        new_str = json.dumps(new_state) if new_state else None
        
        event = AuditEvent(
            workspace_id=workspace_id,
            user_id=user.id if user else None,
            role=user.role if user else "system",
            action_category=action_category,
            action=action,
            target_id=target_id,
            target_type=target_type,
            previous_state=prev_str,
            new_state=new_str,
            reason=reason,
            evidence_id=evidence_id,
            ai_model=ai_model,
            prompt_version=prompt_version,
            regulation_version=regulation_version,
            ip_address=ip_address,
            status=status
        )
        
        db.add(event)
        await db.commit()
        
        logger.info(f"Audit Logged [{action_category}] {action} for workspace {workspace_id}")
        return event
