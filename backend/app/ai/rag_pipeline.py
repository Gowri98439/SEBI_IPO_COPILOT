"""
RAG (Retrieval-Augmented Generation) pipeline for SEBI regulations.
Provides functions to query the SEBI corpus and generate LLM answers grounded in retrieved context.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.ai.llm_client import get_fast_llm, get_llm
from app.ai.prompts import (
    SEBI_EXPERT_SYSTEM,
    SEBI_QUERY_WITH_CONTEXT_TEMPLATE,
)
from app.ai.vector_store import get_sebi_vectorstore, get_workspace_vectorstore

logger = logging.getLogger(__name__)


async def query_sebi_regulations(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Query the indexed SEBI corpus using hybrid retrieval (Dense MMR + BM25 + RRF).

    The BM25 index was previously built on every document upload but never used in queries.
    This function now activates it via Reciprocal Rank Fusion for significantly better
    precision on keyword-heavy regulatory/numeric SEBI clause lookups.

    Args:
        query: Natural language query about SEBI regulations.
        top_k: Number of top results to return.

    Returns:
        List of dicts with keys: content, regulation_id, source, section.
    """
    from app.ai.vector_store import search_bm25, rrf_merge, SEBI_COLLECTION
    try:
        vectorstore = get_sebi_vectorstore()

        # 1. Dense retrieval using MMR
        dense_docs_with_scores = await vectorstore.asimilarity_search_with_relevance_scores(
            query, k=top_k * 2
        )

        # 2. Sparse BM25 retrieval
        bm25_results = search_bm25(query, SEBI_COLLECTION, top_k=top_k * 2)

        # 3. Fuse results using Reciprocal Rank Fusion
        if bm25_results:
            fused = rrf_merge(dense_docs_with_scores, bm25_results, top_n=top_k)
            logger.debug("Hybrid RAG (Dense+BM25+RRF) query '%s' returned %d results.", query, len(fused))
        else:
            # BM25 index not yet built — fall back to dense only
            fused = dense_docs_with_scores[:top_k]
            logger.debug("BM25 index unavailable, using dense-only retrieval for query '%s'.", query)

        results = [
            {
                "content": doc.page_content,
                "regulation_id": doc.metadata.get("regulation_id", ""),
                "source": doc.metadata.get("source_file", ""),
                "section": doc.metadata.get("section", ""),
                "chapter": doc.metadata.get("chapter", ""),
                "regulation_version": doc.metadata.get("regulation_version", "unknown"),
                "effective_date": doc.metadata.get("effective_date", "unknown"),
                "score": float(score),
            }
            for doc, score in fused
        ]
        return results
    except Exception as exc:
        logger.error("Error during RAG query: %s", exc, exc_info=True)
        return []


async def query_workspace_documents(
    query: str,
    workspace_id: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Query uploaded documents for a specific workspace.

    Args:
        query: Natural language query.
        workspace_id: The workspace whose documents to search.
        top_k: Number of results to return.

    Returns:
        List of dicts with keys: content, document_id, filename, page, similarity_score.
    """
    try:
        vectorstore = get_workspace_vectorstore(workspace_id)
        # Use similarity_search_with_relevance_scores to get real retrieval confidence
        docs_with_scores = await vectorstore.asimilarity_search_with_relevance_scores(query, k=top_k)
        return [
            {
                "content": doc.page_content,
                "document_id": doc.metadata.get("document_id", ""),
                "filename": doc.metadata.get("filename", ""),
                "page": doc.metadata.get("page", None),
                "doc_type": doc.metadata.get("doc_type", ""),
                "similarity_score": float(score),
            }
            for doc, score in docs_with_scores
        ]
    except Exception as exc:
        logger.error("Error during workspace RAG query for workspace '%s': %s", workspace_id, exc, exc_info=True)
        return []


async def query_with_llm(query: str, context_docs: list[dict[str, Any]]) -> str:
    """
    Generate an LLM response grounded in retrieved SEBI regulation context.

    Args:
        query: The user's question.
        context_docs: List of regulation chunk dicts (from query_sebi_regulations).

    Returns:
        LLM-generated answer string.
    """
    if not context_docs:
        logger.warning("query_with_llm called with empty context — falling back to LLM-only mode.")
        context_text = "No specific regulations retrieved. Use your general SEBI knowledge, and be explicit about uncertainty."
    else:
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            if "regulation_id" in doc:
                # SEBI document
                reg_id = doc.get("regulation_id", "")
                section = doc.get("section", "")
                source = doc.get("source", "")
                header = f"[{i}] [SEBI Regulation: {reg_id}] — {section} (Source: {source})" if reg_id else f"[{i}] Source: {source}"
            else:
                # Workspace document
                filename = doc.get("filename", "")
                page = doc.get("page", "")
                header = f"[{i}] [Document: {filename}, Page: {page}]"
                
            context_parts.append(f"{header}\n{doc['content']}")
        context_text = "\n\n---\n\n".join(context_parts)

    prompt_text = SEBI_QUERY_WITH_CONTEXT_TEMPLATE.format(
        context=context_text,
        query=query,
    )

    llm = get_llm()
    messages = [
        SystemMessage(content=SEBI_EXPERT_SYSTEM),
        HumanMessage(content=prompt_text),
    ]
    parser = StrOutputParser()
    chain = llm | parser
    response = await chain.ainvoke(messages)
    return response


async def rag_query_full(query: str, workspace_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
    """
    Combined RAG + LLM pipeline: retrieve context, generate grounded answer.

    Args:
        query: User question about SEBI regulations.
        workspace_id: Optional workspace ID to search uploaded documents first.
        top_k: Number of context chunks to retrieve.

    Returns:
        Dict with 'answer', 'sources', and 'context_docs'.
    """
    context_docs = []
    
    # 1. Search workspace documents FIRST if workspace_id is provided
    if workspace_id:
        workspace_docs = await query_workspace_documents(query, workspace_id, top_k=top_k)
        if workspace_docs:
            context_docs.extend(workspace_docs)
            
    # 2. Only supplement using SEBI corpus if needed
    sebi_top_k = 1 if context_docs else top_k
    sebi_docs = await query_sebi_regulations(query, top_k=sebi_top_k)
    if sebi_docs:
        context_docs.extend(sebi_docs)
        
    answer = await query_with_llm(query, context_docs)
    # Fix: workspace documents use 'filename' key, SEBI corpus uses 'source' key.
    # Collect both so user-uploaded document citations are never silently dropped.
    sources = list({
        doc.get("source") or doc.get("filename", "")
        for doc in context_docs
        if doc.get("source") or doc.get("filename")
    })
    return {
        "answer": answer,
        "sources": sources,
        "context_docs": context_docs,
    }


async def build_compliance_context(regulation_description: str, top_k: int = 3) -> tuple[str, str]:
    """
    Retrieve SEBI context relevant to a specific regulation for compliance checking.
    Returns a formatted string ready to inject into a compliance prompt, 
    and a version string indicating the source of the regulation.
    """
    docs = await query_sebi_regulations(regulation_description, top_k=top_k)
    if not docs:
        return "No additional context available from SEBI corpus.", "unknown"
    parts = []
    versions = set()
    for doc in docs:
        reg_id = doc.get("regulation_id", "N/A")
        parts.append(f"[{reg_id}]\n{doc['content']}")
        ver = doc.get("regulation_version", "unknown")
        if ver != "unknown":
            versions.add(ver)
    
    version_str = ", ".join(versions) if versions else "unknown"
    return "\n\n".join(parts), version_str
