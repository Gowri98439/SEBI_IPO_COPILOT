"""
SEBI compliance engine for IPO Copilot.
Defines the SEBI SME IPO checklist and runs individual compliance checks
using RAG-augmented LLM analysis.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.ai.llm_client import get_fast_llm
from app.ai.prompts import (
    COMPLIANCE_CHECK_WITH_CONTEXT_TEMPLATE,
)
from app.ai.rag_pipeline import build_compliance_context
from app.security.prompt_sanitizer import SYSTEM_GUARD

logger = logging.getLogger(__name__)

# Load SEBI rules from JSON registry
SEBI_RULES_PATH = Path(__file__).parent.parent.parent / "data" / "sebi_rules.json"
try:
    with open(SEBI_RULES_PATH, "r", encoding="utf-8") as f:
        SEBI_SME_CHECKLIST = json.load(f)
except Exception as e:
    logger.error("Failed to load sebi_rules.json: %s", e)
    SEBI_SME_CHECKLIST = []


# ---------------------------------------------------------------------------
# Pydantic model for structured compliance check output
# ---------------------------------------------------------------------------


class ComplianceCheckResult(BaseModel):
    """Structured output from a single compliance regulation check."""

    status: str = Field(
        description="Compliance status: 'pass', 'fail', 'warning'",
        pattern="^(pass|fail|warning)$",
    )
    why: str = Field(
        description="Detailed explanation of your finding"
    )
    evidence: str = Field(
        description="Direct quote or reference from the document supporting the finding."
    )
    regulation_reference: str = Field(
        description="The specific SEBI clause or sub-regulation identified.",
        default="",
    )
    confidence_score: float = Field(
        description="Confidence score between 0.0 and 1.0",
        default=1.0,
    )
    source: str = Field(
        description="Document name and page number",
        default="",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Specific improvement suggestions when status is fail or warning.",
    )


# ---------------------------------------------------------------------------
# Single compliance check runner
# ---------------------------------------------------------------------------


async def run_single_compliance_check(
    check_id: str,
    regulation: dict,
    workspace_id: str,
) -> dict:
    """
    Run a compliance check for one regulation against uploaded document texts using targeted RAG.

    Args:
        check_id: Regulation identifier (e.g., 'ICDR_REG_26').
        regulation: Dict with keys: id, name, description, category, severity.
        workspace_id: The ID of the workspace containing the documents.

    Returns:
        Dict with keys: check_id, regulation_name, status, evidence, ai_reasoning,
                        suggestions, category, severity, source.
    """
    logger.info("Running compliance check: %s — %s for workspace: %s", check_id, regulation.get("title", regulation.get("name", "Unknown")), workspace_id)

    # Step 1: RAG query for regulatory context from SEBI corpus
    rag_context = await build_compliance_context(
        regulation_description=regulation["check"],
        top_k=3,
    )

    # Step 2: RAG query for workspace document evidence
    from app.ai.rag_pipeline import query_workspace_documents
    query_str = f"{regulation['title']} {regulation['check']} {' '.join(regulation.get('keywords', []))}"
    workspace_docs = await query_workspace_documents(query_str, workspace_id, top_k=6)
    
    if not workspace_docs:
        return {
            "check_id": check_id,
            "regulation_name": regulation["title"],
            "status": "not_applicable",
            "evidence": "No document text available or relevant for this regulation.",
            "ai_reasoning": "No relevant evidence was found in the workspace documents.",
            "suggestions": ["Upload relevant documents to enable compliance checking."],
            "category": regulation.get("category", "general"),
            "severity": regulation.get("severity", "medium"),
            "source": "",
        }

    # Prepare document text
    doc_parts = []
    for doc in workspace_docs:
        filename = doc.get('filename', 'Unknown')
        page = doc.get('page', '?')
        doc_parts.append(f"[File: {filename}, Page: {page}]\n{doc['content']}")
        
    combined_doc_text = "\n\n=== DOCUMENT SEPARATOR ===\n\n".join(doc_parts)

    # Step 3: Build prompt and call LLM with structured output
    llm = get_fast_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ComplianceCheckResult)

    user_prompt = COMPLIANCE_CHECK_WITH_CONTEXT_TEMPLATE.format(
        regulation_id=regulation["id"],
        regulation_name=regulation["title"],
        regulation_description=regulation["check"],
        rag_context=rag_context,
        document_text=combined_doc_text,
    )

    system_message_content = f"{SYSTEM_GUARD}\n\nAct as a SEBI Compliance Officer. Evaluate the provided document against the specific regulation. Reply exactly in the requested JSON structure."
    
    messages = [
        SystemMessage(content=system_message_content),
        HumanMessage(content=user_prompt),
    ]

    try:
        result: ComplianceCheckResult = await structured_llm.ainvoke(messages)
        
        # Calculate combined confidence
        # Since retrieval score from ChromaDB is distance (0 is perfect), we synthesize a naive score.
        # Ideally, we would use the actual doc score. We'll extract a naive retrieval score for now.
        retrieval_score = 0.85 if workspace_docs else 0.0
        combined_confidence = (0.6 * retrieval_score) + (0.4 * result.confidence_score)
        
        status = result.status
        if combined_confidence < 0.6 and status == "pass":
            status = "warning"
            
        return {
            "check_id": check_id,
            "regulation_name": regulation["title"],
            "status": status,
            "confidence": "strong" if combined_confidence > 0.8 else ("low" if combined_confidence < 0.6 else "medium"),
            "regulation_reference": result.regulation_reference,
            "evidence": result.evidence,
            "ai_reasoning": result.why,
            "suggestions": result.suggestions,
            "source": result.source,
            "category": regulation.get("category", "general"),
            "severity": regulation.get("severity", "medium"),
        }
    except Exception as exc:
        logger.error("Compliance check failed for %s: %s", check_id, exc, exc_info=True)
        return {
            "check_id": check_id,
            "regulation_name": regulation["title"],
            "status": "warning",
            "evidence": "",
            "ai_reasoning": f"AI analysis could not complete: {exc}",
            "suggestions": ["Please retry the compliance check."],
            "category": regulation.get("category", "general"),
            "severity": regulation.get("severity", "medium"),
            "source": "",
        }


async def run_all_compliance_checks(workspace_id: str) -> list[dict]:
    """
    Run all SEBI_SME_CHECKLIST checks concurrently against the workspace documents using targeted RAG.
    
    Args:
        workspace_id: The ID of the workspace containing the documents to evaluate.
        
    Returns:
        List of compliance check result dicts.
    """
    import asyncio

    logger.info("Running concurrent compliance checks for %d rules for workspace %s", len(SEBI_SME_CHECKLIST), workspace_id)

    # We will use asyncio.gather to run all 30 checks in parallel.
    # Each check handles its own RAG retrieval and LLM evaluation.
    tasks = []
    for reg in SEBI_SME_CHECKLIST:
        task = asyncio.create_task(
            run_single_compliance_check(reg["id"], reg, workspace_id)
        )
        tasks.append(task)
        
    final_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and handle any top-level exceptions that escaped run_single_compliance_check
    safe_results = []
    for i, res in enumerate(final_results):
        if isinstance(res, Exception):
            reg = SEBI_SME_CHECKLIST[i]
            logger.error("Critical failure during compliance check %s: %s", reg["id"], res)
            safe_results.append({
                "check_id": reg["id"],
                "regulation_name": reg["title"],
                "status": "warning",
                "evidence": "",
                "ai_reasoning": f"Critical AI execution failure: {res}",
                "suggestions": ["Please retry the compliance check later."],
                "category": reg.get("category", "general"),
                "severity": reg.get("severity", "medium"),
                "source": "",
            })
        else:
            safe_results.append(res)

    return safe_results


def get_compliance_summary(check_results: list[dict]) -> dict:
    """
    Compute summary statistics from a list of compliance check results.

    Returns:
        Dict with total, pass_count, fail_count, warning_count, not_applicable_count,
        overall_status, and compliance_score (%).
    """
    total = len(check_results)
    pass_count = sum(1 for r in check_results if r["status"] == "pass")
    fail_count = sum(1 for r in check_results if r["status"] == "fail")
    warning_count = sum(1 for r in check_results if r["status"] == "warning")
    na_count = sum(1 for r in check_results if r["status"] == "not_applicable")
    applicable = total - na_count
    score = round((pass_count / applicable * 100) if applicable > 0 else 0, 1)

    if fail_count == 0 and warning_count == 0:
        overall_status = "compliant"
    elif fail_count > 0:
        overall_status = "non_compliant"
    else:
        overall_status = "needs_review"

    return {
        "total": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warning_count": warning_count,
        "not_applicable_count": na_count,
        "overall_status": overall_status,
        "compliance_score": score,
    }
