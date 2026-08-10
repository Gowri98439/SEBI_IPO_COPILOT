"""
Government-Style Workflow Engine
Enforces strict Role-Based Access Control (RBAC) and logs state transitions.
Roles: ADMIN, REGULATORY_OFFICER, REVIEWER, MB (Merchant Banker), COMPANY_USER
"""
from __future__ import annotations

import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.enterprise import WorkflowState, ReviewDecision
from app.models.user import User

logger = logging.getLogger(__name__)

# Define allowed roles
ROLES = ["ADMIN", "REGULATORY_OFFICER", "REVIEWER", "MB", "COMPANY_USER"]

# Define valid state transitions
ALLOWED_TRANSITIONS = {
    "SUBMISSION": ["SCREENING"],
    "SCREENING": ["VALIDATION", "CORRECTION"],
    "VALIDATION": ["AI_ANALYSIS", "CORRECTION"],
    "AI_ANALYSIS": ["COMPLIANCE_REVIEW"],
    "COMPLIANCE_REVIEW": ["RISK_REVIEW", "CORRECTION"],
    "RISK_REVIEW": ["HUMAN_REVIEW", "CORRECTION"],
    "HUMAN_REVIEW": ["APPROVED", "CORRECTION", "REJECTED"],
    "CORRECTION": ["SUBMISSION"],
    "APPROVED": [],
    "REJECTED": []
}

# Define Role permissions for transitioning states
ROLE_PERMISSIONS = {
    "COMPANY_USER": {"SUBMISSION": ["SCREENING"], "CORRECTION": ["SUBMISSION"]},
    "MB": {"SUBMISSION": ["SCREENING"], "CORRECTION": ["SUBMISSION"]},
    "REVIEWER": {
        "SCREENING": ["VALIDATION", "CORRECTION"],
        "VALIDATION": ["AI_ANALYSIS", "CORRECTION"],
        "COMPLIANCE_REVIEW": ["RISK_REVIEW", "CORRECTION"],
        "RISK_REVIEW": ["HUMAN_REVIEW", "CORRECTION"]
    },
    "REGULATORY_OFFICER": {
        "HUMAN_REVIEW": ["APPROVED", "CORRECTION", "REJECTED"]
    },
    "ADMIN": ALLOWED_TRANSITIONS # Admin can do any valid transition
}

class WorkflowEngine:
    
    @staticmethod
    async def get_or_create_workflow(db: AsyncSession, workspace_id: str) -> WorkflowState:
        stmt = select(WorkflowState).where(WorkflowState.workspace_id == workspace_id)
        result = await db.execute(stmt)
        state = result.scalars().first()
        
        if not state:
            state = WorkflowState(workspace_id=workspace_id, current_stage="SUBMISSION")
            db.add(state)
            await db.commit()
            
        return state

    @staticmethod
    async def transition_state(
        db: AsyncSession,
        workspace_id: str,
        user: User,
        target_state: str,
        notes: Optional[str] = None
    ) -> WorkflowState:
        """
        Attempt to transition the workflow state for a workspace.
        Enforces RBAC and valid state transitions.
        """
        state = await WorkflowEngine.get_or_create_workflow(db, workspace_id)
        current_state = state.current_stage
        role = user.role.upper()
        
        # 1. Validate Role
        if role not in ROLE_PERMISSIONS:
            raise PermissionError(f"Role {role} is not authorized to transition states.")
            
        # 2. Validate Transition
        allowed_targets = ROLE_PERMISSIONS[role].get(current_state, [])
        if target_state not in allowed_targets:
            raise PermissionError(f"User with role {role} cannot transition from {current_state} to {target_state}.")
            
        # 3. Apply Transition
        logger.info(f"Transitioning workspace {workspace_id} from {current_state} to {target_state} by {user.email}")
        state.current_stage = target_state
        state.updated_at = datetime.now(timezone.utc)
        
        # Log the transition in ReviewDecision as an audit trail record
        decision = ReviewDecision(
            workspace_id=workspace_id,
            user_id=user.id,
            target_type="WorkflowState",
            target_id=state.id,
            decision=target_state,
            notes=f"Transitioned from {current_state} to {target_state}. Notes: {notes or 'None'}"
        )
        db.add(decision)
        
        await db.commit()
        return state
