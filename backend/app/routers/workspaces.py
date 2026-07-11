import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.company import Company
from app.models.document import Document
from app.models.compliance_check import ComplianceCheck
from app.models.validation_result import ValidationResult
from app.models.audit_event import AuditEvent
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from fastapi.responses import Response
from app.security.rate_limiter import limiter
from app.security.audit import log_action

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    workspace = Workspace(
        company_id=str(data.company_id),
        name=data.name,
        status="draft",
        created_by=current_user.id,
    )
    db.add(workspace)
    await db.flush()
    await db.refresh(workspace)
    return workspace  # type: ignore[return-value]


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkspaceResponse]:
    result = await db.execute(
        select(Workspace)
        .where(Workspace.created_by == current_user.id)
        .order_by(Workspace.created_at.desc())
    )
    return list(result.scalars().all())  # type: ignore[return-value]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    result = await db.execute(
        select(Workspace).where(Workspace.id == str(workspace_id), Workspace.created_by == current_user.id)
    )
    workspace = result.scalars().first()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    return workspace  # type: ignore[return-value]


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    result = await db.execute(
        select(Workspace).where(Workspace.id == str(workspace_id), Workspace.created_by == current_user.id)
    )
    workspace = result.scalars().first()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )
    update_dict = data.model_dump(exclude_none=True)
    for field, value in update_dict.items():
        setattr(workspace, field, value)
    db.add(workspace)
    await db.flush()
    await db.refresh(workspace)
    return workspace  # type: ignore[return-value]

@router.get("/{workspace_id}/export/report.pdf")
@limiter.limit("10/minute")
async def export_workspace_report(
    request: Request,
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.report_service import ReportService
    
    workspace = await db.scalar(select(Workspace).where(Workspace.id == str(workspace_id), Workspace.created_by == current_user.id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    company = await db.scalar(select(Company).where(Company.id == workspace.company_id))
    documents = (await db.scalars(select(Document).where(Document.workspace_id == str(workspace_id)))).all()
    checks = (await db.scalars(select(ComplianceCheck).where(ComplianceCheck.workspace_id == str(workspace_id)))).all()
    
    # We need validation results for all documents in the workspace
    doc_ids = [d.id for d in documents]
    if doc_ids:
        validations = (await db.scalars(select(ValidationResult).where(ValidationResult.document_id.in_(doc_ids)))).all()
    else:
        validations = []
        
    audit_events = (await db.scalars(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == str(workspace_id))
        .order_by(AuditEvent.created_at.desc())
    )).all()
    
    import asyncio
    pdf_bytes = await asyncio.to_thread(ReportService.generate_workspace_report, workspace, company, documents, checks, validations, audit_events)
    
    await log_action(
        db=db,
        action="EXPORT_REPORT",
        action_category="EXPORT",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=str(workspace_id),
        target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id),
        details="Exported executive PDF report"
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=IPO_Copilot_Report_{workspace.name.replace(' ', '_')}.pdf"
        }
    )

@router.post("/demo/seed", response_model=WorkspaceResponse)
async def seed_demo_environment(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.utils.demo_seeder import seed_demo_workspace
    workspace = await seed_demo_workspace(db, str(current_user.id))
    return workspace  # type: ignore[return-value]


@router.get("/{workspace_id}/audit-logs", tags=["Audit Trail"])
async def get_audit_logs(
    workspace_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return audit events for a workspace, most recent first."""
    # Verify access
    ws = await db.scalar(
        select(Workspace).where(
            Workspace.id == str(workspace_id),
            Workspace.created_by == current_user.id,
        )
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == str(workspace_id))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "action": e.action,
            "action_category": getattr(e, "action_category", "SYSTEM"),
            "details": e.details or "",
            "ip_address": e.ip_address or "",
            "status": e.status or "SUCCESS",
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in events
    ]

