"""
DRHP Router — API endpoints for DRHP generation
SEBI ICDR Regulations 2018 — SME IPO
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.drhp import DrhpRequest, DrhpJobResponse, DrhpStatusResponse
from app.services.drhp_service import generate_drhp_async, get_job_status, get_job_pdf
from app.security.audit import log_action
from sqlalchemy import select

router = APIRouter(prefix="/workspaces", tags=["DRHP Generator"])


@router.post(
    "/{workspace_id}/drhp/generate",
    response_model=DrhpJobResponse,
    status_code=202,
)
async def generate_drhp(
    workspace_id: uuid.UUID,
    request_body: DrhpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DrhpJobResponse:
    """Start an async DRHP generation job. Returns a job_id to poll status."""
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == str(workspace_id),
            Workspace.created_by == current_user.id,
        )
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    job_id = await generate_drhp_async(request_body)

    await log_action(
        db=db,
        action="DRHP_GENERATION_STARTED",
        action_category="DRHP",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=str(workspace_id),
        target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id),
        details=f"DRHP generation started for company: {request_body.company.name}",
    )

    return DrhpJobResponse(
        job_id=job_id,
        status="processing",
        message="DRHP generation started. Poll /status/{job_id} for progress.",
    )


@router.get(
    "/{workspace_id}/drhp/status/{job_id}",
    response_model=DrhpStatusResponse,
)
async def drhp_status(
    workspace_id: uuid.UUID,
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> DrhpStatusResponse:
    """Poll the status and progress of a DRHP generation job."""
    job = get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return DrhpStatusResponse(
        job_id=job_id,
        status=job.get("status", "processing"),
        progress_pct=job.get("progress_pct", 0),
        message=job.get("message", ""),
    )


@router.get(
    "/{workspace_id}/drhp/download/{job_id}",
)
async def download_drhp(
    workspace_id: uuid.UUID,
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the generated DRHP PDF once the job is complete."""
    job = get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="DRHP generation not yet complete")

    pdf_bytes = get_job_pdf(job_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="PDF not available")

    await log_action(
        db=db,
        action="DRHP_DOWNLOADED",
        action_category="DRHP",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=str(workspace_id),
        target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id),
        details=f"DRHP document downloaded (job: {job_id})",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=DRHP_Draft.pdf",
            "Content-Length": str(len(pdf_bytes)),
        },
    )
