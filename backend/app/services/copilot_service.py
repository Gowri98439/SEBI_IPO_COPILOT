import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copilot import CopilotMessage, CopilotSession


class CopilotService:
    @staticmethod
    async def create_session(
        db: AsyncSession, workspace_id: str, user_id: str
    ) -> CopilotSession:
        session = CopilotSession(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_sessions(
        db: AsyncSession, workspace_id: str
    ) -> list[CopilotSession]:
        result = await db.execute(
            select(CopilotSession)
            .where(CopilotSession.workspace_id == workspace_id)
            .order_by(CopilotSession.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_messages(
        db: AsyncSession, session_id: str
    ) -> list[CopilotMessage]:
        result = await db.execute(
            select(CopilotMessage)
            .where(CopilotMessage.session_id == session_id)
            .order_by(CopilotMessage.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def save_user_message(
        db: AsyncSession,
        session_id: str,
        content: str,
        action_type: str | None = None,
    ) -> CopilotMessage:
        message = CopilotMessage(
            session_id=session_id,
            role="user",
            content=content,
            action_type=action_type,
            metadata={},
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    @staticmethod
    async def save_assistant_message(
        db: AsyncSession,
        session_id: str,
        content: str,
    ) -> CopilotMessage:
        message = CopilotMessage(
            session_id=session_id,
            role="assistant",
            content=content,
            action_type=None,
            metadata={},
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message
