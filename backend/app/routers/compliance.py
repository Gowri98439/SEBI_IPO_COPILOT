from fastapi import APIRouter, BackgroundTasks, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.compliance import ComplianceCheckResponse
from app.services.compliance_service import ComplianceService
from app.ai.background_tasks import run_compliance_checks_task
from app.security.audit import log_action
from app.security.rate_limiter import limiter
from app.models.workspace import Workspace
from fastapi import HTTPException
from sqlalchemy import select

async def _verify_check_access(db: AsyncSession, check_id: str, user_id: str) -> None:
    check = await ComplianceService.get_check(db, check_id)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == check.workspace_id, Workspace.created_by == user_id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to access this check")

router = APIRouter(tags=["Compliance"])


@router.post(
    "/workspaces/{workspace_id}/compliance/run",
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def run_compliance(
    request: Request,
    workspace_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    checks = await ComplianceService.run_checks(db, workspace_id)
    # AI evaluation runs asynchronously — one LLM call per SEBI regulation
    background_tasks.add_task(run_compliance_checks_task, workspace_id)
    await log_action(
        db=db,
        action="COMPLIANCE_RUN_STARTED",
        action_category="COMPLIANCE",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=workspace_id,
        target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=workspace_id,
        details="Full AI compliance check triggered",
    )
    return {
        "message": "Compliance run triggered",
        "checks_created": len(checks),
        "workspace_id": workspace_id,
    }


@router.get(
    "/workspaces/{workspace_id}/compliance",
    response_model=list[ComplianceCheckResponse],
)
async def list_compliance_checks(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ComplianceCheckResponse]:
    checks = await ComplianceService.get_checks(db, workspace_id)
    return checks  # type: ignore[return-value]


@router.get(
    "/workspaces/{workspace_id}/compliance/{check_id}",
    response_model=ComplianceCheckResponse,
)
async def get_compliance_check(
    workspace_id: str,
    check_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceCheckResponse:
    await _verify_check_access(db, check_id, str(current_user.id))
    check = await ComplianceService.get_check(db, check_id)
    return check  # type: ignore[return-value]
