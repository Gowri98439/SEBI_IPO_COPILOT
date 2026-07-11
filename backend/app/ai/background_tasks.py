"""
Background task runner functions for IPO Copilot AI processing.
These are called via FastAPI BackgroundTasks (fire-and-forget async jobs).
Each function manages its own DB session and updates the database on completion or failure.

Column mapping (matches existing SQLAlchemy models exactly):
  Document:         id, workspace_id, name, doc_type, file_path, file_size,
                    mime_type, status, uploaded_by, created_at, updated_at
  ValidationResult: id, document_id, status, issues, missing_info,
                    summary, ai_model, created_at
  ComplianceCheck:  id, workspace_id, check_type, regulation, status,
                    evidence, ai_reasoning, created_at, updated_at
  DraftReview:      id, workspace_id, section, draft_content, ai_feedback,
                    status, reviewed_by, created_at, updated_at
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.database import async_session_factory
from app.ai.document_validator import validate_document
from app.ai.compliance_engine import SEBI_SME_CHECKLIST, run_single_compliance_check
from app.ai.rag_pipeline import query_sebi_regulations
from app.ai.llm_client import get_fast_llm
from app.ai.prompts import DRAFT_REVIEW_SYSTEM, DRAFT_REVIEW_TEMPLATE

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task 1: Document Validation + Missing Information Detection
# ---------------------------------------------------------------------------


async def run_document_validation_task(
    doc_id: str,
    file_path: str,
    doc_type: str,
) -> None:
    """
    Background task: Run AI validation on an uploaded document and persist results.

    Uses only columns present on ValidationResult and Document models:
      - ValidationResult: status, issues, missing_info, summary, ai_model
      - Document: status
    """
    logger.info("[validation_task] Starting for doc_id=%s, doc_type=%s", doc_id, doc_type)

    async with async_session_factory() as session:
        try:
            from app.models.document import Document
            from app.models.validation_result import ValidationResult

            # Mark document as processing
            document = await session.get(Document, doc_id)
            if not document:
                logger.error("[validation_task] Document %s not found.", doc_id)
                return

            document.status = "processing"  # type: ignore
            await session.commit()

            from app.utils.file_storage import get_file_path
            abs_file_path = get_file_path(file_path)

            # Run AI validation pipeline (returns dict with issues, missing_info, summary)
            result = await validate_document(
                file_path=abs_file_path,
                doc_type=doc_type or "other",
                document_id=doc_id,
            )

            # Upsert: if a pending ValidationResult already exists for this doc, update it
            from sqlalchemy import select
            stmt = select(ValidationResult).where(
                ValidationResult.document_id == doc_id
            ).order_by(ValidationResult.created_at.desc())
            existing = (await session.execute(stmt)).scalars().first()

            if existing:
                existing.status = result["status"]
                existing.issues = result.get("issues", [])
                existing.missing_info = result.get("missing_info", [])
                existing.summary = result.get("summary", "")
                existing.ai_model = result.get("ai_model", "gpt-4o-mini")
            else:
                validation_record = ValidationResult(
                    document_id=doc_id,
                    status=result["status"],
                    issues=result.get("issues", []),
                    missing_info=result.get("missing_info", []),
                    summary=result.get("summary", ""),
                    ai_model=result.get("ai_model", "gpt-4o-mini"),
                )
                session.add(validation_record)

            # Update document status
            document.status = "validated" if result["status"] == "completed" else "failed"  # type: ignore
            await session.commit()

            logger.info(
                "[validation_task] Completed doc_id=%s — status=%s, issues=%d, missing=%d",
                doc_id,
                result["status"],
                len(result.get("issues", [])),
                len(result.get("missing_info", [])),
            )

        except Exception as exc:
            logger.error("[validation_task] Failed for doc_id=%s: %s", doc_id, exc, exc_info=True)
            try:
                await session.rollback()
                from app.models.document import Document
                document = await session.get(Document, doc_id)
                if document:
                    document.status = "failed"  # type: ignore
                    await session.commit()
            except Exception as inner_exc:
                logger.error("[validation_task] Could not set document status=failed: %s", inner_exc)


# ---------------------------------------------------------------------------
# Task 2: SEBI Compliance Engine
# ---------------------------------------------------------------------------


async def run_compliance_checks_task(workspace_id: str) -> None:
    """
    Background task: Run all SEBI compliance checks for a workspace.

    Uses only columns present on ComplianceCheck model:
      - check_type (maps to regulation["id"])
      - regulation  (maps to regulation["name"])
      - status, evidence, ai_reasoning
    """
    logger.info("[compliance_task] Starting for workspace_id=%s", workspace_id)

    async with async_session_factory() as session:
        try:
            from app.models.document import Document
            from app.models.compliance_check import ComplianceCheck
            from sqlalchemy import select
            from app.ai.document_validator import extract_text_from_pdf

            # Fetch validated (or uploaded) documents in the workspace
            stmt = select(Document).where(
                Document.workspace_id == workspace_id,
                Document.status.in_(["validated", "uploaded"]),
            )
            result = await session.execute(stmt)
            documents = result.scalars().all()

            if not documents:
                logger.warning("[compliance_task] No documents for workspace %s.", workspace_id)
                return

            from app.ai.compliance_engine import SEBI_SME_CHECKLIST, run_all_compliance_checks

            logger.info(
                "[compliance_task] Running %d checks against workspace %s.",
                len(SEBI_SME_CHECKLIST), workspace_id,
            )

            # Call the concurrent function passing the workspace_id
            batch_results = await run_all_compliance_checks(workspace_id)
            
            for check_result in batch_results:
                reg_id = check_result["check_id"]
                try:
                    # Upsert: check_type = regulation id, regulation = regulation name
                    existing_stmt = select(ComplianceCheck).where(
                        ComplianceCheck.workspace_id == workspace_id,
                        ComplianceCheck.check_type == reg_id,
                    )
                    existing_result = await session.execute(existing_stmt)
                    existing_check = existing_result.scalars().first()

                    # evidence: store as dict with reasoning and suggestions
                    evidence_payload = {
                        "evidence": check_result.get("evidence", ""),
                        "confidence": check_result.get("confidence", "strong"),
                        "regulation_reference": check_result.get("regulation_reference", ""),
                        "suggestions": check_result.get("suggestions", []),
                        "category": check_result.get("category", "general"),
                        "severity": check_result.get("severity", "medium"),
                        "source": check_result.get("source", ""),
                    }

                    if existing_check:
                        existing_check.status = check_result["status"]
                        existing_check.evidence = evidence_payload  # type: ignore
                        existing_check.ai_reasoning = check_result["ai_reasoning"]
                    else:
                        new_check = ComplianceCheck(
                            workspace_id=workspace_id,
                            check_type=reg_id,
                            regulation=check_result["regulation_name"],
                            status=check_result["status"],
                            evidence=evidence_payload,
                            ai_reasoning=check_result["ai_reasoning"],
                        )
                        session.add(new_check)

                    if check_result["status"] in ("fail", "warning"):
                        from app.models.review import ReviewTask
                        task_stmt = select(ReviewTask).where(
                            ReviewTask.workspace_id == workspace_id,
                            ReviewTask.task_type == "validate",
                            ReviewTask.notes.like(f"%[{reg_id}]%"),
                        )
                        existing_task = (await session.execute(task_stmt)).scalars().first()
                        if not existing_task:
                            new_task = ReviewTask(
                                workspace_id=workspace_id,
                                assigned_to="Compliance Officer",
                                task_type="validate",
                                status="open",
                                notes=f"[{reg_id}] {check_result['regulation_name']} requires review: {check_result.get('ai_reasoning', 'Flagged by compliance engine')}",
                            )
                            session.add(new_task)

                    await session.commit()
                    logger.info("[compliance_task] %s — %s: %s", workspace_id, reg_id, check_result["status"])

                except Exception as exc:
                    logger.error("[compliance_task] Saving check %s failed: %s", reg_id, exc, exc_info=True)
                    await session.rollback()

            logger.info("[compliance_task] Completed for workspace %s. Triggering summary generation.", workspace_id)
            # Call executive summary generation here since compliance checks are done
            await generate_executive_summary_task(workspace_id, session)

        except Exception as exc:
            logger.error(
                "[compliance_task] Fatal error for workspace %s: %s", workspace_id, exc, exc_info=True
            )
            try:
                await session.rollback()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Task 3: AI Draft Review
# ---------------------------------------------------------------------------


async def run_draft_review_task(
    review_id: str,
    section: str,
    draft_content: str,
) -> None:
    """
    Background task: AI review of a draft offer document section.

    Uses only columns present on DraftReview model:
      - status, ai_feedback
    """
    logger.info("[draft_review_task] Starting review_id=%s, section='%s'", review_id, section)

    async with async_session_factory() as session:
        try:
            from app.models.review import DraftReview
            from langchain_core.messages import HumanMessage, SystemMessage
            from pydantic import BaseModel, Field

            review = await session.get(DraftReview, review_id)
            if not review:
                logger.error("[draft_review_task] DraftReview %s not found.", review_id)
                return

            review.status = "processing"  # type: ignore
            await session.commit()

            # Step 1: RAG-query SEBI corpus for section-specific requirements
            rag_docs = await query_sebi_regulations(
                f"IPO offer document {section} section requirements SEBI ICDR disclosures",
                top_k=4,
            )
            if rag_docs:
                rag_context = "\n\n".join(
                    f"[{d.get('regulation_id', 'N/A')}]\n{d['content'][:600]}"
                    for d in rag_docs
                )
            else:
                rag_context = "General SEBI ICDR Regulations 2018 requirements apply for this section."

            # Step 2: Build prompt
            truncated_draft = draft_content[:100000] if len(draft_content) > 100000 else draft_content
            user_prompt = DRAFT_REVIEW_TEMPLATE.format(
                section_name=section,
                rag_context=rag_context,
                draft_content=truncated_draft,
            )

            # Step 3: Structured output Pydantic models
            class FeedbackItem(BaseModel):
                issue: str = Field(description="Description of the problem or gap.")
                suggestion: str = Field(description="Specific improvement recommendation.")
                severity: str = Field(description="high, medium, or low", pattern="^(high|medium|low)$")
                ref_rule: str = Field(description="Applicable SEBI regulation reference.")

            class DraftReviewOutput(BaseModel):
                feedback: list[FeedbackItem] = Field(default_factory=list)
                overall_rating: str = Field(
                    description="compliant, needs_revision, or non_compliant",
                    pattern="^(compliant|needs_revision|non_compliant)$",
                )
                summary: str = Field(description="Brief overall assessment.")

            # Step 4: LLM call with structured output
            llm = get_fast_llm(temperature=0.1)
            structured_llm = llm.with_structured_output(DraftReviewOutput)
            messages = [
                SystemMessage(content=DRAFT_REVIEW_SYSTEM),
                HumanMessage(content=user_prompt),
            ]
            result: DraftReviewOutput = await structured_llm.ainvoke(messages)

            # Step 5: Persist — ai_feedback column stores the full structured result
            review.ai_feedback = {  # type: ignore
                "feedback": [item.model_dump() for item in result.feedback],
                "overall_rating": result.overall_rating,
                "summary": result.summary,
            }
            review.status = "completed"  # type: ignore
            await session.commit()

            logger.info(
                "[draft_review_task] Completed review_id=%s — %d items, rating=%s",
                review_id, len(result.feedback), result.overall_rating,
            )

        except Exception as exc:
            logger.error(
                "[draft_review_task] Failed for review_id=%s: %s", review_id, exc, exc_info=True
            )
            try:
                await session.rollback()
                from app.models.review import DraftReview
                review = await session.get(DraftReview, review_id)
                if review:
                    review.status = "failed"  # type: ignore
                    review.ai_feedback = {"error": str(exc), "feedback": [], "summary": "AI review failed."}  # type: ignore
                    await session.commit()
            except Exception as inner_exc:
                logger.error("[draft_review_task] Could not update status=failed: %s", inner_exc)

# ---------------------------------------------------------------------------
# Task 4: AI Executive Summary
# ---------------------------------------------------------------------------

async def generate_executive_summary_task(workspace_id: str, existing_session=None) -> None:
    """
    Generate an AI Executive Summary based on all Validation Results and Compliance Checks.
    """
    logger.info("[executive_summary] Starting for workspace_id=%s", workspace_id)
    
    async def _run(session):
        from sqlalchemy import select
        from app.models.workspace import Workspace
        from app.models.compliance_check import ComplianceCheck
        from app.models.validation_result import ValidationResult
        from app.models.document import Document
        from langchain_core.messages import HumanMessage, SystemMessage
        from pydantic import BaseModel, Field

        workspace = await session.get(Workspace, workspace_id)
        if not workspace:
            return

        # Fetch compliance checks
        checks_result = await session.execute(
            select(ComplianceCheck).where(ComplianceCheck.workspace_id == workspace_id)
        )
        checks = checks_result.scalars().all()
        failed_checks = [c for c in checks if c.status == "fail"]
        warning_checks = [c for c in checks if c.status == "warning"]

        # Fetch validation issues
        issues_result = await session.execute(
            select(ValidationResult).join(Document, ValidationResult.document_id == Document.id)
            .where(Document.workspace_id == workspace_id)
        )
        validations = issues_result.scalars().all()
        
        all_missing = []
        for v in validations:
            all_missing.extend(v.missing_info or [])

        # Build prompt context
        context = f"Company: {workspace.name}\n"
        context += f"Failed Compliance Checks: {len(failed_checks)}\n"
        for c in failed_checks[:5]:
            context += f" - {c.regulation}: {c.ai_reasoning}\n"
        
        context += f"\nMissing Disclosures: {len(all_missing)}\n"
        for m in all_missing[:5]:
            desc = m.get('description', '') if isinstance(m, dict) else str(m)
            context += f" - {desc}\n"

        system_prompt = (
            "You are a senior Big 4 (Deloitte/EY/PwC/KPMG) partner specializing in SEBI SME IPO advisory. "
            "Write a highly professional, board-ready executive summary of the SME's IPO readiness "
            "based strictly on the provided compliance data. Maintain a formal, authoritative, and precise tone."
        )
        user_prompt = f"Data:\n{context}\n\nOutput a JSON conforming exactly to the required schema. Ensure every recommendation includes a citation."

        class Recommendation(BaseModel):
            action: str = Field(description="The recommended priority action")
            citation: str = Field(description="Evidence or regulation cited for this recommendation")

        class ExecutiveSummaryOutput(BaseModel):
            executive_overview: str = Field(description="Executive Overview")
            business_risks: list[str] = Field(description="Business Risks")
            compliance_gaps: list[str] = Field(description="Compliance Gaps")
            critical_missing_information: list[str] = Field(description="Critical Missing Information")
            priority_actions: list[str] = Field(description="Priority Actions")
            estimated_filing_readiness: int = Field(description="Estimated Filing Readiness as a percentage 0-100")
            top_recommendations: list[Recommendation] = Field(description="Top Recommendations with citations")

        llm = get_fast_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(ExecutiveSummaryOutput)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        try:
            result = await structured_llm.ainvoke(messages)
            workspace.executive_summary = result.model_dump_json()
            await session.commit()
            logger.info("[executive_summary] Successfully generated for %s", workspace_id)
        except Exception as exc:
            logger.error("[executive_summary] Failed: %s", exc)

    if existing_session:
        await _run(existing_session)
    else:
        async with async_session_factory() as session:
            await _run(session)

