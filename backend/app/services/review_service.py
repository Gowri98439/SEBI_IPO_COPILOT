import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import DraftReview, ReviewTask
from app.schemas.review import DraftReviewCreate, DraftReviewUpdate, ReviewTaskCreate, ReviewTaskUpdate


class ReviewService:
    @staticmethod
    async def create_draft_review(
        db: AsyncSession, data: DraftReviewCreate
    ) -> DraftReview:
        review = DraftReview(
            workspace_id=str(data.workspace_id),
            section=data.section,
            draft_content=data.draft_content,
            ai_feedback=[],
            status="pending",
        )
        db.add(review)
        await db.flush()
        await db.commit()
        await db.refresh(review)
        return review

    @staticmethod
    async def get_draft_reviews(
        db: AsyncSession, workspace_id: str
    ) -> list[DraftReview]:
        result = await db.execute(
            select(DraftReview)
            .where(DraftReview.workspace_id == workspace_id)
            .order_by(DraftReview.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_draft_review(db: AsyncSession, review_id: str) -> DraftReview:
        result = await db.execute(
            select(DraftReview).where(DraftReview.id == review_id)
        )
        review = result.scalars().first()
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft review not found",
            )
        return review

    @staticmethod
    async def update_draft_review(
        db: AsyncSession, review_id: str, update_data: DraftReviewUpdate
    ) -> DraftReview:
        review = await ReviewService.get_draft_review(db, review_id)
        update_dict = update_data.model_dump(exclude_none=True)
        for field, value in update_dict.items():
            setattr(review, field, value)
        db.add(review)
        await db.flush()
        await db.refresh(review)
        return review

    @staticmethod
    async def create_review_task(
        db: AsyncSession, data: ReviewTaskCreate
    ) -> ReviewTask:
        task = ReviewTask(
            workspace_id=str(data.workspace_id),
            assigned_to=str(data.assigned_to) if data.assigned_to else None,
            task_type=data.task_type,
            status="open",
            notes=data.notes,
            due_date=data.due_date,
        )
        db.add(task)
        await db.flush()
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_review_tasks(
        db: AsyncSession, workspace_id: str
    ) -> list[ReviewTask]:
        result = await db.execute(
            select(ReviewTask)
            .where(ReviewTask.workspace_id == workspace_id)
            .order_by(ReviewTask.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_review_task(db: AsyncSession, task_id: str) -> ReviewTask:
        result = await db.execute(
            select(ReviewTask).where(ReviewTask.id == task_id)
        )
        task = result.scalars().first()
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review task not found"
            )
        return task

    @staticmethod
    async def update_review_task(
        db: AsyncSession, task_id: str, update_data: ReviewTaskUpdate
    ) -> ReviewTask:
        task = await ReviewService.get_review_task(db, task_id)
        update_dict = update_data.model_dump(exclude_none=True)
        for field, value in update_dict.items():
            setattr(task, field, value)
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task
