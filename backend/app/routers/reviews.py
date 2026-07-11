from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.review import (
    DraftReviewCreate,
    DraftReviewResponse,
    DraftReviewUpdate,
    ReviewTaskCreate,
    ReviewTaskResponse,
    ReviewTaskUpdate,
)
from app.services.review_service import ReviewService
from app.ai.background_tasks import run_draft_review_task
from app.utils.audit import log_audit_event
from app.models.workspace import Workspace
from fastapi import HTTPException
from sqlalchemy import select

async def _verify_review_access(db: AsyncSession, review_id: str, user_id: str) -> None:
    review = await ReviewService.get_draft_review(db, review_id)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == review.workspace_id, Workspace.created_by == user_id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to access this review")

async def _verify_task_access(db: AsyncSession, task_id: str, user_id: str) -> None:
    from app.models.review import ReviewTask
    task = await db.scalar(select(ReviewTask).where(ReviewTask.id == task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    workspace = await db.scalar(select(Workspace).where(Workspace.id == task.workspace_id, Workspace.created_by == user_id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

router = APIRouter(tags=["Reviews"])


@router.post(
    "/workspaces/{workspace_id}/drafts",
    response_model=DraftReviewResponse,
    status_code=201,
)
async def create_draft_review(
    workspace_id: str,
    data: DraftReviewCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftReviewResponse:
    review = await ReviewService.create_draft_review(db, data)
    # Trigger AI review asynchronously if draft content is provided
    if data.draft_content and data.draft_content.strip():
        background_tasks.add_task(
            run_draft_review_task,
            str(review.id),
            data.section,
            data.draft_content,
        )
        await log_audit_event(
            db=db,
            workspace_id=workspace_id,
            action="DRAFT_REVIEW_STARTED",
            user_id=str(current_user.id),
            target_id=str(review.id),
            target_type="draft_review",
            details=f"AI Review started for section: {data.section}",
        )
    return review  # type: ignore[return-value]


@router.get(
    "/workspaces/{workspace_id}/drafts",
    response_model=list[DraftReviewResponse],
)
async def list_draft_reviews(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DraftReviewResponse]:
    reviews = await ReviewService.get_draft_reviews(db, workspace_id)
    return reviews  # type: ignore[return-value]


@router.get("/drafts/{review_id}", response_model=DraftReviewResponse)
async def get_draft_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftReviewResponse:
    await _verify_review_access(db, review_id, str(current_user.id))
    review = await ReviewService.get_draft_review(db, review_id)
    return review  # type: ignore[return-value]


@router.patch("/drafts/{review_id}", response_model=DraftReviewResponse)
async def update_draft_review(
    review_id: str,
    data: DraftReviewUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftReviewResponse:
    await _verify_review_access(db, review_id, str(current_user.id))
    review = await ReviewService.update_draft_review(db, review_id, data)
    # Re-run AI review when draft content is updated
    if data.draft_content and data.draft_content.strip():  # type: ignore
        background_tasks.add_task(
            run_draft_review_task,
            str(review.id),
            review.section,  # type: ignore
            data.draft_content,  # type: ignore
        )
        await log_audit_event(
            db=db,
            workspace_id=str(review.workspace_id),
            action="DRAFT_REVIEW_UPDATED",
            user_id=str(current_user.id),
            target_id=str(review.id),
            target_type="draft_review",
            details=f"Draft content updated for section: {review.section}, AI review restarted.",
        )
    
    if data.status:
        await log_audit_event(
            db=db,
            workspace_id=str(review.workspace_id),
            action="DRAFT_REVIEW_STATUS_CHANGED",
            user_id=str(current_user.id),
            target_id=str(review.id),
            target_type="draft_review",
            details=f"Status changed to {data.status} by {current_user.email}",
        )

    return review  # type: ignore[return-value]


@router.post(
    "/workspaces/{workspace_id}/reviews",
    response_model=ReviewTaskResponse,
    status_code=201,
)
async def create_review_task(
    workspace_id: str,
    data: ReviewTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewTaskResponse:
    task = await ReviewService.create_review_task(db, data)
    return task  # type: ignore[return-value]


@router.get(
    "/workspaces/{workspace_id}/reviews",
    response_model=list[ReviewTaskResponse],
)
async def list_review_tasks(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReviewTaskResponse]:
    tasks = await ReviewService.get_review_tasks(db, workspace_id)
    return tasks  # type: ignore[return-value]


@router.patch("/reviews/{task_id}", response_model=ReviewTaskResponse)
async def update_review_task(
    task_id: str,
    data: ReviewTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewTaskResponse:
    await _verify_task_access(db, task_id, str(current_user.id))
    task = await ReviewService.update_review_task(db, task_id, data)
    return task  # type: ignore[return-value]
