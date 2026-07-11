"""
Document validation AI pipeline for IPO Copilot.
Extracts text from PDFs, RAG-queries for applicable SEBI regulations,
and uses an LLM with structured output to identify issues and missing disclosures.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import pdfplumber
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.ai.llm_client import get_fast_llm
from app.ai.prompts import (
    DOCUMENT_VALIDATION_WITH_CONTEXT_TEMPLATE,
    DOCUMENT_VALIDATOR_SYSTEM,
)
from app.ai.rag_pipeline import query_sebi_regulations

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models for structured LLM output
# ---------------------------------------------------------------------------


class ValidationIssue(BaseModel):
    """A single compliance, missing, or format issue found in a document."""

    type: str = Field(
        description="Type of issue: 'compliance', 'missing', or 'format'",
        pattern="^(compliance|missing|format)$",
    )
    severity: str = Field(
        description="Severity level: 'high', 'medium', or 'low'",
        pattern="^(high|medium|low)$",
    )
    description: str = Field(description="Clear description of the issue found.")
    page: Optional[int] = Field(default=None, description="Estimated page number where the issue appears.")
    rule: str = Field(description="Applicable SEBI regulation ID (e.g., ICDR_REG_26).")
    why: str = Field(description="Why this is an issue.")
    evidence: str = Field(description="Excerpt from the text causing the issue.")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0.")
    source: str = Field(description="Document name and page number.")


class MissingInfo(BaseModel):
    """A mandatory disclosure or field that is absent from the document."""

    field: str = Field(description="Name of the missing field or disclosure.")
    section: str = Field(description="Section of the offer document where this should appear.")
    required_by: str = Field(description="SEBI regulation requiring this disclosure.")
    description: str = Field(description="What information is needed and why it is mandatory.")


class DocumentValidationResult(BaseModel):
    """Structured output from the document validation LLM chain."""

    issues: List[ValidationIssue] = Field(default_factory=list)
    missing_info: List[MissingInfo] = Field(default_factory=list)
    summary: str = Field(description="Executive summary of overall compliance status.")


# ---------------------------------------------------------------------------
# Document type → relevant SEBI query map
# ---------------------------------------------------------------------------

DOC_TYPE_QUERIES: dict[str, list[str]] = {
    "prospectus": [
        "SME IPO prospectus mandatory disclosures ICDR",
        "offer document contents requirements SEBI ICDR Chapter V",
        "risk factors disclosure requirements SME IPO",
    ],
    "draft_red_herring_prospectus": [
        "DRHP draft red herring prospectus requirements SEBI",
        "mandatory disclosures draft offer document SME IPO",
        "financials disclosure DRHP ICDR regulations",
    ],
    "memorandum_of_association": [
        "memorandum of association requirements IPO SEBI",
        "objects clause main objects ancillary objects company",
    ],
    "articles_of_association": [
        "articles of association requirements IPO listing",
        "shareholder rights articles IPO SEBI",
    ],
    "financial_statements": [
        "financial statements restated financials IPO SEBI ICDR",
        "auditor report financial disclosure requirements SME IPO",
        "profit loss balance sheet IPO requirements",
    ],
    "auditor_report": [
        "auditor report IPO requirements SEBI ICDR",
        "statutory audit report qualifications SME IPO",
    ],
    "certificate": [
        "compliance certificate SME IPO SEBI requirements",
        "promoter contribution certificate lock-in ICDR",
    ],
    "other": [
        "SME IPO document requirements SEBI ICDR",
        "disclosure requirements IPO offer documents",
    ],
}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_text_from_pdf(file_path: str, max_pages: int = 50) -> tuple[str, int]:
    """
    Extract text from a PDF file using pdfplumber.

    Args:
        file_path: Absolute path to the PDF file.
        max_pages: Maximum number of pages to process (avoids very long docs).

    Returns:
        Tuple of (extracted_text, total_pages).
    """
    text_parts: list[str] = []
    total_pages = 0
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages)
            for i, page in enumerate(pdf.pages[:pages_to_process]):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(f"--- Page {i + 1} ---\n{page_text}")
    except Exception as exc:
        logger.error("Failed to extract text from PDF '%s': %s", file_path, exc, exc_info=True)
        raise RuntimeError(f"PDF text extraction failed: {exc}") from exc

    full_text = "\n\n".join(text_parts)
    logger.info("Extracted %d chars from %d/%d pages of '%s'",
                len(full_text), min(total_pages, max_pages), total_pages, file_path)
    return full_text, total_pages


def truncate_text_for_llm(text: str, max_chars: int = 12000) -> str:
    """
    Truncate document text to fit within LLM context window.
    Preserves beginning and end of document (most important sections).
    """
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    start = text[:half]
    end = text[-half:]
    return f"{start}\n\n[... DOCUMENT TRUNCATED — middle section omitted for length ...]\n\n{end}"


# ---------------------------------------------------------------------------
# Main validation pipeline
# ---------------------------------------------------------------------------


async def validate_document(
    file_path: str,
    doc_type: str,
    document_id: str,
) -> dict:
    """
    Full AI validation pipeline for an IPO offer document.

    Steps:
    1. Extract text from PDF
    2. Identify applicable SEBI regulation queries for doc_type
    3. RAG-query the SEBI corpus for requirements
    4. LLM structured-output analysis
    5. Return validated result dict

    Args:
        file_path: Absolute path to the PDF/document file.
        doc_type: Type of document (e.g., 'prospectus', 'financial_statements').
        document_id: UUID of the document record in the DB.

    Returns:
        Dict matching the DocumentValidationResult schema plus status and ai_model fields.
    """
    logger.info("Starting AI validation for document_id=%s, doc_type=%s", document_id, doc_type)

    # Step 1: Extract text
    import asyncio
    try:
        document_text, total_pages = await asyncio.to_thread(extract_text_from_pdf, file_path)
    except RuntimeError as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "issues": [],
            "missing_info": [],
            "summary": "Document could not be processed — PDF text extraction failed.",
            "ai_model": "none",
        }

    if not document_text.strip():
        return {
            "status": "failed",
            "error": "No readable text found in document. It may be a scanned/image PDF.",
            "issues": [],
            "missing_info": [],
            "summary": "Document appears to be a scanned image PDF — OCR required for analysis.",
            "ai_model": "none",
        }

    # Step 2 & 3: RAG-query applicable regulations
    queries = DOC_TYPE_QUERIES.get(doc_type, DOC_TYPE_QUERIES["other"])
    all_context_docs: list[dict] = []
    for q in queries:
        docs = await query_sebi_regulations(q, top_k=3)
        all_context_docs.extend(docs)

    # Deduplicate by content
    seen_contents: set[str] = set()
    unique_context_docs = []
    for doc in all_context_docs:
        content_key = doc["content"][:100]
        if content_key not in seen_contents:
            seen_contents.add(content_key)
            unique_context_docs.append(doc)

    # Build context string
    if unique_context_docs:
        context_parts = []
        for doc in unique_context_docs[:8]:  # cap at 8 chunks
            reg_id = doc.get("regulation_id", "N/A")
            context_parts.append(f"[{reg_id}]\n{doc['content']}")
        rag_context = "\n\n---\n\n".join(context_parts)
    else:
        rag_context = "SEBI ICDR Regulations 2018 apply. Refer to general SME IPO disclosure requirements."

    # Step 4: LLM structured output
    llm = get_fast_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(DocumentValidationResult)

    truncated_text = truncate_text_for_llm(document_text, max_chars=10000)
    user_prompt = DOCUMENT_VALIDATION_WITH_CONTEXT_TEMPLATE.format(
        doc_type=doc_type.replace("_", " ").title(),
        rag_context=rag_context,
        document_text=truncated_text,
    )

    messages = [
        SystemMessage(content=DOCUMENT_VALIDATOR_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    try:
        result: DocumentValidationResult = await structured_llm.ainvoke(messages)
    except Exception as exc:
        logger.error("LLM structured output failed for document_id=%s: %s", document_id, exc, exc_info=True)
        return {
            "status": "failed",
            "error": f"AI analysis failed: {exc}",
            "issues": [],
            "missing_info": [],
            "summary": "AI validation could not complete due to an internal error.",
            "ai_model": "gpt-4o-mini",
        }

    # Step 5: Format and return
    return {
        "status": "completed",
        "issues": [issue.model_dump() for issue in result.issues],
        "missing_info": [mi.model_dump() for mi in result.missing_info],
        "summary": result.summary,
        "ai_model": "gpt-4o-mini",
        "pages_analyzed": min(total_pages, 50),
        "total_pages": total_pages,
        "document_id": document_id,
    }
