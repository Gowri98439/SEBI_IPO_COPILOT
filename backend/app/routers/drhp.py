"""
DRHP Router — Enterprise v2 API
Extends existing v1 endpoints (backward-compatible) with:
- POST /{workspace_id}/drhp/v2/generate  — Enterprise pipeline with DrhpRequestV2
- GET  /{workspace_id}/drhp/v2/status/{job_id}  — Rich status with stage details
- GET  /{workspace_id}/drhp/stream/{job_id}      — SSE real-time progress
- GET  /{workspace_id}/drhp/v2/download/{job_id}  — DRHP PDF download
- GET  /{workspace_id}/drhp/v2/intelligence/{job_id}  — Intelligence Report download

All v1 endpoints (generate, status, download) remain unchanged.
"""
import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.drhp import DrhpJobResponse, DrhpRequest, DrhpStatusResponse
from app.schemas.drhp_v2 import DrhpJobResponseV2, DrhpRequestV2, DrhpStatusResponseV2
from app.security.audit import log_action

# v1 imports (preserved)
from app.services.drhp_service import (
    generate_drhp_async,
    get_job_pdf,
    get_job_status,
)

# v2 imports (new pipeline)
from app.ai.drhp_pipeline import (
    get_job as get_v2_job,
    get_job_intelligence_pdf,
    get_job_pdf as get_v2_job_pdf,
    start_pipeline,
)

router = APIRouter(prefix="/workspaces", tags=["DRHP Generator"])

# ── Workspace ownership helper ───────────────────────────────────────────────

async def _verify_workspace(workspace_id: uuid.UUID, user: User, db: AsyncSession) -> Workspace:
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == str(workspace_id),
            Workspace.created_by == user.id,
        )
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


# ══════════════════════════════════════════════════════════════════════════════
#  V1 ENDPOINTS — PRESERVED UNCHANGED
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{workspace_id}/drhp/generate",
    response_model=DrhpJobResponse,
    status_code=202,
    summary="[v1] Start DRHP generation (legacy)",
)
async def generate_drhp(
    workspace_id: uuid.UUID,
    request_body: DrhpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DrhpJobResponse:
    """Start an async DRHP generation job (v1 — template-based). Returns a job_id."""
    await _verify_workspace(workspace_id, current_user, db)
    job_id = await generate_drhp_async(request_body)
    await log_action(
        db=db, action="DRHP_GENERATION_STARTED", action_category="DRHP", result="SUCCESS",
        user_id=str(current_user.id), target_id=str(workspace_id), target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id),
        details=f"DRHP v1 generation started for: {request_body.company.name}",
    )
    return DrhpJobResponse(
        job_id=job_id,
        status="processing",
        message="DRHP generation started. Poll /status/{job_id} for progress.",
    )


@router.get(
    "/{workspace_id}/drhp/status/{job_id}",
    response_model=DrhpStatusResponse,
    summary="[v1] Poll DRHP job status (legacy)",
)
async def drhp_status(
    workspace_id: uuid.UUID,
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> DrhpStatusResponse:
    """Poll the status of a v1 DRHP job."""
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
    summary="[v1] Download DRHP PDF (legacy)",
)
async def download_drhp(
    workspace_id: uuid.UUID,
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the generated DRHP PDF (v1)."""
    await _verify_workspace(workspace_id, current_user, db)
    job = get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="DRHP generation not yet complete")
    pdf_bytes = get_job_pdf(job_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="PDF not available")
    await log_action(
        db=db, action="DRHP_DOWNLOADED", action_category="DRHP", result="SUCCESS",
        user_id=str(current_user.id), target_id=str(workspace_id), target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id), details=f"DRHP document downloaded (job: {job_id})",
    )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=DRHP_Draft.pdf",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  V2 ENDPOINTS — ENTERPRISE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{workspace_id}/drhp/v2/generate",
    response_model=DrhpJobResponseV2,
    status_code=202,
    summary="[v2] Start Enterprise DRHP generation",
)
async def generate_drhp_v2(
    workspace_id: uuid.UUID,
    request_body: DrhpRequestV2,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DrhpJobResponseV2:
    """
    Start an enterprise DRHP generation job using the 12-stage pipeline.
    Returns a job_id immediately — generation runs asynchronously.

    Features:
    - LLM-assisted section generation with hallucination guard
    - Financial ratio computation (25+ ratios)
    - 20-check cross-section consistency validation
    - SEBI compliance validation
    - Professional PDF with bookmarks and TOC
    - Separate IPO Intelligence Report
    - Real-time SSE progress via /stream/{job_id}
    """
    await _verify_workspace(workspace_id, current_user, db)

    job_id = await start_pipeline(
        req=request_body,
        workspace_id=str(workspace_id),
    )

    await log_action(
        db=db, action="DRHP_V2_GENERATION_STARTED", action_category="DRHP", result="SUCCESS",
        user_id=str(current_user.id), target_id=str(workspace_id), target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id),
        details=f"DRHP v2 pipeline started for: {request_body.company.name}",
    )

    return DrhpJobResponseV2(
        job_id=job_id,
        status="pending",
        message="Enterprise DRHP pipeline started. Stream progress at /drhp/stream/{job_id}",
        stream_url=f"/workspaces/{workspace_id}/drhp/stream/{job_id}",
        estimated_minutes=5,
    )


@router.get(
    "/{workspace_id}/drhp/v2/status/{job_id}",
    response_model=DrhpStatusResponseV2,
    summary="[v2] Get enterprise DRHP job status",
)
async def drhp_status_v2(
    workspace_id: uuid.UUID,
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> DrhpStatusResponseV2:
    """Get detailed status of an enterprise DRHP pipeline job."""
    # Check both v2 and v1 job stores
    job = get_v2_job(job_id)
    if job is None:
        job = get_job_status(job_id)  # v1 fallback
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return DrhpStatusResponseV2(
        job_id=job_id,
        status=job.get("status", "processing"),
        progress_pct=job.get("progress_pct", 0),
        current_stage=job.get("current_stage"),
        current_section=job.get("current_section"),
        message=job.get("message", ""),
        sections_completed=job.get("sections_completed", 0),
        sections_total=job.get("sections_total", 0),
        consistency_status=job.get("consistency_status"),
        compliance_status=job.get("compliance_status"),
        errors=job.get("errors", []),
        warnings=job.get("warnings", [])[:10],
        drhp_ready=job.get("drhp_ready", False),
        intelligence_report_ready=job.get("intelligence_report_ready", False),
        total_time_seconds=job.get("total_time_seconds"),
    )


@router.get(
    "/{workspace_id}/drhp/stream/{job_id}",
    summary="[v2] SSE stream for real-time generation progress",
)
async def drhp_stream(
    workspace_id: uuid.UUID,
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events stream for real-time DRHP generation progress.

    Events:
    - progress: {"pct": 42, "stage": "Section Generator", "message": "Generating: Business Overview"}
    - warning: {"message": "..."}
    - complete: {"drhp_ready": true, "intelligence_report_ready": true}
    - error: {"message": "..."}

    Connect with:
    const es = new EventSource('/workspaces/{id}/drhp/stream/{job_id}');
    es.addEventListener('progress', (e) => { ... });
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        last_pct = -1
        max_polls = 1800  # 30 minutes max at 1s interval
        for _ in range(max_polls):
            job = get_v2_job(job_id) or get_job_status(job_id)
            if not job:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                return

            status = job.get("status", "processing")
            pct = job.get("progress_pct", 0)
            stage = job.get("current_stage", "")
            message = job.get("message", "")
            warnings = job.get("warnings", [])

            # Only emit progress events when something changed
            if pct != last_pct:
                payload = json.dumps({
                    "pct": pct,
                    "stage": stage,
                    "message": message,
                    "status": status,
                })
                yield f"event: progress\ndata: {payload}\n\n"
                last_pct = pct

            # Emit warning events
            if warnings:
                for w in warnings[-3:]:  # Last 3 new warnings
                    yield f"event: warning\ndata: {json.dumps({'message': w})}\n\n"

            if status == "done":
                yield f"event: complete\ndata: {json.dumps({'drhp_ready': job.get('drhp_ready', False), 'intelligence_report_ready': job.get('intelligence_report_ready', False), 'total_time_seconds': job.get('total_time_seconds', 0)})}\n\n"
                return
            elif status == "error":
                yield f"event: error\ndata: {json.dumps({'message': message})}\n\n"
                return

            # Keep-alive ping
            yield ": ping\n\n"
            await asyncio.sleep(1.0)

        yield f"event: error\ndata: {json.dumps({'message': 'Stream timeout'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{workspace_id}/drhp/v2/download/{job_id}",
    summary="[v2] Download enterprise DRHP PDF",
)
async def download_drhp_v2(
    workspace_id: uuid.UUID,
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the enterprise DRHP PDF from a v2 pipeline job."""
    await _verify_workspace(workspace_id, current_user, db)
    job = get_v2_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") not in ("done",):
        raise HTTPException(status_code=409, detail=f"DRHP not ready — status: {job.get('status')}")
    if not job.get("drhp_ready"):
        raise HTTPException(status_code=409, detail="DRHP PDF not available — check job status for errors")

    pdf_bytes = get_v2_job_pdf(job_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="PDF not found in job store")

    await log_action(
        db=db, action="DRHP_V2_DOWNLOADED", action_category="DRHP", result="SUCCESS",
        user_id=str(current_user.id), target_id=str(workspace_id), target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id), details=f"Enterprise DRHP PDF downloaded (job: {job_id})",
    )
    company_name = job.get("company_name")
    if company_name:
        import re
        safe_name = re.sub(r'[\/\\:*?"<>|]', '', company_name).strip().replace(" ", "_")
        filename = f"{safe_name}_DRHP.pdf"
    else:
        filename = "IPO_Copilot_DRHP.pdf"

    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get(
    "/{workspace_id}/drhp/v2/intelligence/{job_id}",
    summary="[v2] Download IPO Intelligence Report PDF",
)
async def download_intelligence_report(
    workspace_id: uuid.UUID,
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the separate IPO Intelligence Report PDF from a v2 pipeline job."""
    await _verify_workspace(workspace_id, current_user, db)
    job = get_v2_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get("intelligence_report_ready"):
        raise HTTPException(status_code=409, detail="Intelligence Report not yet available")

    pdf_bytes = get_job_intelligence_pdf(job_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="Intelligence Report PDF not found")

    await log_action(
        db=db, action="IPO_INTELLIGENCE_DOWNLOADED", action_category="DRHP", result="SUCCESS",
        user_id=str(current_user.id), target_id=str(workspace_id), target_type="workspace",
        ip_address=request.client.host if request.client else None,
        workspace_id=str(workspace_id), details=f"Intelligence Report downloaded (job: {job_id})",
    )
    company_name = job.get("company_name")
    if company_name:
        import re
        safe_name = re.sub(r'[\/\\:*?"<>|]', '', company_name).strip().replace(" ", "_")
        filename = f"{safe_name}_Intelligence_Report.pdf"
    else:
        filename = "IPO_Copilot_Intelligence_Report.pdf"

    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
