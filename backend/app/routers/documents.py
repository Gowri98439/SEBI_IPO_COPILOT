import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.document import DocumentResponse, ValidationResultResponse
from app.services.document_service import DocumentService
from app.ai.background_tasks import run_document_validation_task
from app.security.audit import log_action
from app.security.rate_limiter import limiter
from app.security.file_validator import validate_upload
from app.models.workspace import Workspace

async def _verify_doc_access(db: AsyncSession, doc_id: str, user_id: str) -> DocumentResponse:
    doc = await DocumentService.get_document(db, doc_id)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == doc.workspace_id, Workspace.created_by == user_id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    return doc

router = APIRouter(tags=["Documents"])


@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    from app.models.workspace import Workspace
    workspace = await db.scalar(select(Workspace).where(Workspace.id == str(workspace_id), Workspace.created_by == current_user.id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to upload to this workspace")
        
    try:
        file_content = await file.read()
        safe_filename = validate_upload(file_content, file.filename or "unnamed")
        
        doc = await DocumentService.upload_from_bytes(
            db, str(workspace_id), file_content, file.filename or "unnamed", file.content_type, doc_type, str(current_user.id), safe_filename
        )
        await log_action(
            db=db,
            action="DOCUMENT_UPLOADED",
            action_category="DOCUMENT",
            result="SUCCESS",
            user_id=str(current_user.id),
            target_id=str(doc.id),
            target_type="document",
            ip_address=request.client.host if request.client else None,
            workspace_id=str(workspace_id),
            details=f"Uploaded document: {file.filename}",
        )
        return doc  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(exc)}")


@router.get("/workspaces/{workspace_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    from app.models.workspace import Workspace
    workspace = await db.scalar(select(Workspace).where(Workspace.id == str(workspace_id), Workspace.created_by == current_user.id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
        
    docs = await DocumentService.list_documents(db, str(workspace_id))
    return docs  # type: ignore[return-value]


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = await _verify_doc_access(db, str(doc_id), str(current_user.id))
    return doc  # type: ignore[return-value]


@router.delete("/documents/{doc_id}", response_model=DocumentResponse)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = await _verify_doc_access(db, str(doc_id), str(current_user.id))
    doc = await DocumentService.soft_delete(db, str(doc_id))
    await log_action(
        db=db,
        action="DOCUMENT_DELETED",
        action_category="DOCUMENT",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=str(doc.id),
        target_type="document",
        workspace_id=str(doc.workspace_id),
        details=f"Deleted document: {doc.name}",
    )
    return doc  # type: ignore[return-value]


@router.post("/documents/{doc_id}/validate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_validation(
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    doc = await _verify_doc_access(db, str(doc_id), str(current_user.id))
    validation = await DocumentService.trigger_validation(db, str(doc_id))
    # AI validation + missing information detection runs asynchronously
    background_tasks.add_task(
        run_document_validation_task,
        str(doc.id),
        doc.file_path,  # type: ignore
        doc.doc_type or "other",
    )
    await log_action(
        db=db,
        action="VALIDATION_STARTED",
        action_category="VALIDATION",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=str(doc.id),
        target_type="document",
        workspace_id=str(doc.workspace_id),
        details=f"AI Validation started for: {doc.name}",
    )
    return {
        "message": "Validation triggered",
        "validation_id": str(validation.id),
        "status": validation.status,
    }


@router.get(
    "/documents/{doc_id}/validation-result",
    response_model=ValidationResultResponse | None,
)
async def get_validation_result(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationResultResponse | None:
    await _verify_doc_access(db, str(doc_id), str(current_user.id))
    result = await DocumentService.get_validation_result(db, str(doc_id))
    return result  # type: ignore[return-value]


@router.get("/documents/{doc_id}/versions")
async def get_versions(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    await _verify_doc_access(db, str(doc_id), str(current_user.id))
    versions = await DocumentService.get_versions(db, str(doc_id))
    return [
        {
            "id": str(v.id),
            "document_id": str(v.document_id),
            "version_number": v.version_number,
            "file_path": v.file_path,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]
