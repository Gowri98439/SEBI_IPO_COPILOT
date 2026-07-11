import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.copilot import CopilotSession
from app.schemas.copilot import MessageCreate, MessageResponse, SessionResponse
from app.services.copilot_service import CopilotService
from app.ai.rag_pipeline import query_sebi_regulations
from app.utils.security import decode_token
from fastapi import HTTPException
from app.security.rate_limiter import limiter
from app.security.prompt_sanitizer import scan_for_injection
from app.security.audit import log_action


async def get_current_user_sse(
    token: str | None = Query(default=None),
) -> User:
    """
    Auth dependency for SSE endpoints.
    Accepts JWT via ?token= query param because the browser's native
    EventSource cannot set the Authorization header.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing token query parameter")
    payload = decode_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    from app.database import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def _verify_session_access(db: AsyncSession, session_id: str, user_id: str) -> None:
    session = await db.scalar(select(CopilotSession).where(CopilotSession.id == session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    workspace = await db.scalar(select(Workspace).where(Workspace.id == session.workspace_id, Workspace.created_by == user_id))
    if not workspace:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

router = APIRouter(tags=["Copilot"])


@router.post(
    "/workspaces/{workspace_id}/copilot/sessions",
    response_model=SessionResponse,
    status_code=201,
)
async def create_session(
    request: Request,
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    session = await CopilotService.create_session(
        db, workspace_id, str(current_user.id)
    )
    await log_action(
        db=db,
        action="COPILOT_SESSION_CREATED",
        action_category="COPILOT",
        result="SUCCESS",
        user_id=str(current_user.id),
        target_id=str(session.id),
        target_type="copilot_session",
        ip_address=request.client.host if request.client else None,
        workspace_id=workspace_id,
        details="Started Copilot session",
    )
    return session  # type: ignore[return-value]


@router.get(
    "/workspaces/{workspace_id}/copilot/sessions",
    response_model=list[SessionResponse],
)
async def list_sessions(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionResponse]:
    sessions = await CopilotService.get_sessions(db, workspace_id)
    return sessions  # type: ignore[return-value]


@router.post(
    "/copilot/sessions/{session_id}/message",
    response_model=MessageResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    session_id: str,
    body: MessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await _verify_session_access(db, session_id, str(current_user.id))
    
    is_injected = await scan_for_injection(body.content, db, str(current_user.id))
    if is_injected:
        raise HTTPException(status_code=400, detail="Prompt injection detected and flagged.")
        
    user_msg = await CopilotService.save_user_message(
        db, session_id, body.content, body.action_type
    )
    return user_msg  # type: ignore[return-value]


@router.get("/copilot/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    await _verify_session_access(db, session_id, str(current_user.id))
    messages = await CopilotService.get_messages(db, session_id)
    return messages  # type: ignore[return-value]

from app.ai.copilot_agent import run_copilot_agent
from app.models.copilot import CopilotSession
from sqlalchemy import select
import uuid

async def _sse_generator(session_id: str) -> AsyncGenerator[str, None]:
    """Server-Sent Events generator: stream AI agent response for latest user message."""
    from app.database import async_session_factory
    
    # 1. Fetch session
    async with async_session_factory() as db:
        result = await db.execute(select(CopilotSession).where(CopilotSession.id == session_id))
        session = result.scalars().first()
        if not session:
            yield "data: [DONE]\n\n"
            return
    
        workspace_id = str(session.workspace_id)
    
        # 2. Get session history and wait for the user message to be committed
        db_messages = []
        retries = 10
        while retries > 0:
            await db.rollback()
            db_messages = await CopilotService.get_messages(db, session_id)
            if db_messages and db_messages[-1].role == "user":  # type: ignore
                break
            await asyncio.sleep(0.5)
            retries -= 1
    
        if not db_messages or db_messages[-1].role != "user":  # type: ignore
            # Nothing to reply to
            yield "data: [DONE]\n\n"
            return
    
        user_message = db_messages[-1].content
        history = [{"role": m.role, "content": m.content} for m in db_messages[:-1]]

    def format_sse(text: str) -> str:
        # Multi-line SSE payload
        return "".join(f"data: {line}\n" for line in text.split("\n")) + "\n"

    # 3. Run agent and stream chunks
    full_response = ""
    try:
        async for chunk in run_copilot_agent(user_message, history, workspace_id):  # type: ignore
            full_response += chunk
            yield format_sse(chunk)
    except Exception as exc:
        err_msg = f"Error generating response: {exc}"
        full_response += "\n\n" + err_msg
        yield format_sse(f"\n\n{err_msg}")

    # 4. Save final assistant message to DB
    if full_response:
        async with async_session_factory() as db:
            await CopilotService.save_assistant_message(db, session_id, full_response)
            await db.commit()

    yield "data: [DONE]\n\n"


@router.get("/copilot/sessions/{session_id}/stream")
async def stream_session(
    session_id: str,
    current_user: User = Depends(get_current_user_sse),
) -> StreamingResponse:
    from app.database import async_session_factory
    async with async_session_factory() as db:
        await _verify_session_access(db, session_id, str(current_user.id))
        
    return StreamingResponse(
        _sse_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/copilot/rag-search")
async def search_regulations(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search SEBI regulations via RAG for interactive citations."""
    docs = await query_sebi_regulations(q, top_k=1)
    if docs:
        return docs[0]
    return {"regulation_id": q, "content": "Regulation details not found in corpus.", "source": ""}


# ---------------------------------------------------------------------------
# Simple non-streaming chat endpoint (used by the CopilotPage frontend)
# ---------------------------------------------------------------------------

from pydantic import BaseModel as PydanticBaseModel

class ChatRequest(PydanticBaseModel):
    message: str
    history: list[dict] = []

@router.post("/workspaces/{workspace_id}/copilot/chat")
@limiter.limit("30/minute")
async def copilot_chat(
    request: Request,
    workspace_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Simple synchronous chat endpoint for the SEBI Advisor.
    Uses RAG to fetch relevant regulations then answers via LLM.
    API is used ONLY for assistance/Q&A — no document generation.
    """
    import logging
    logger = logging.getLogger(__name__)

    user_message = body.message.strip()
    if not user_message:
        return {"response": "Please enter a question."}

    try:
        # 1. RAG retrieval from SEBI regulation corpus
        rag_docs = await query_sebi_regulations(user_message, top_k=4)
        rag_context = ""
        if rag_docs:
            parts = []
            for doc in rag_docs:
                reg_id = doc.get("regulation_id", "N/A")
                section = doc.get("section", "")
                content = doc.get("content", "")[:500]
                parts.append(f"[{reg_id} — {section}]\n{content}")
            rag_context = "\n\n---\n\n".join(parts)
        else:
            rag_context = "No specific SEBI regulation found. Provide a general answer based on SEBI ICDR 2018."

        # 2. Build messages for LLM
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        from app.ai.llm_client import get_llm

        system_prompt = (
            "You are an expert SEBI regulatory advisor specialising in SME IPOs and DRHP preparation. "
            "Answer questions accurately based on SEBI ICDR Regulations 2018, SEBI LODR Regulations, "
            "and other applicable SEBI circulars. Be precise, professional, and cite regulation numbers. "
            "Do not use emojis. Keep responses concise but complete. "
            "If the question is outside SEBI/IPO scope, politely redirect.\n\n"
            f"Relevant SEBI Regulations:\n{rag_context}"
        )

        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history (last 6 turns)
        for turn in body.history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        # 3. Call LLM
        llm = get_llm(temperature=0.1)
        result = await llm.ainvoke(messages)
        answer = result.content if hasattr(result, "content") else str(result)

        # 4. Log to audit
        await log_action(
            db=db,
            action="COPILOT_QUERY",
            action_category="COPILOT",
            result="SUCCESS",
            user_id=str(current_user.id),
            target_id=workspace_id,
            target_type="workspace",
            ip_address=request.client.host if request.client else None,
            workspace_id=workspace_id,
            details=f"Query: {user_message[:100]}",
        )

        return {"response": answer, "rag_sources": len(rag_docs)}

    except Exception as exc:
        logger.error("copilot_chat failed: %s", exc, exc_info=True)
        return {
            "response": (
                "I encountered an issue retrieving the answer. "
                "Please check that the SEBI regulation corpus is indexed and try again. "
                f"Error: {type(exc).__name__}"
            )
        }
