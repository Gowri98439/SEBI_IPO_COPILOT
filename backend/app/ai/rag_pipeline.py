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
    Query the indexed SEBI corpus and return the most relevant regulation chunks.

    Args:
        query: Natural language query about SEBI regulations.
        top_k: Number of top results to return.

    Returns:
        List of dicts with keys: content, regulation_id, source, section.
    """
    try:
        vectorstore = get_sebi_vectorstore()
        retriever = vectorstore.as_retriever(
            search_type="mmr",  # Maximal Marginal Relevance for diversity
            search_kwargs={"k": top_k, "fetch_k": top_k * 3},
        )
        docs = await retriever.ainvoke(query)
        results = [
            {
                "content": doc.page_content,
                "regulation_id": doc.metadata.get("regulation_id", ""),
                "source": doc.metadata.get("source_file", ""),
                "section": doc.metadata.get("section", ""),
                "chapter": doc.metadata.get("chapter", ""),
                "score": doc.metadata.get("score", None),
            }
            for doc in docs
        ]
        logger.debug("RAG query '%s' returned %d results.", query, len(results))
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
        List of dicts with keys: content, document_id, filename, page.
    """
    try:
        vectorstore = get_workspace_vectorstore(workspace_id)
        retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
        docs = await retriever.ainvoke(query)
        return [
            {
                "content": doc.page_content,
                "document_id": doc.metadata.get("document_id", ""),
                "filename": doc.metadata.get("filename", ""),
                "page": doc.metadata.get("page", None),
                "doc_type": doc.metadata.get("doc_type", ""),
            }
            for doc in docs
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
    sources = list({doc["source"] for doc in context_docs if doc.get("source")})
    return {
        "answer": answer,
        "sources": sources,
        "context_docs": context_docs,
    }


async def build_compliance_context(regulation_description: str, top_k: int = 3) -> str:
    """
    Retrieve SEBI context relevant to a specific regulation for compliance checking.
    Returns a formatted string ready to inject into a compliance prompt.
    """
    docs = await query_sebi_regulations(regulation_description, top_k=top_k)
    if not docs:
        return "No additional context available from SEBI corpus."
    parts = []
    for doc in docs:
        reg_id = doc.get("regulation_id", "N/A")
        parts.append(f"[{reg_id}]\n{doc['content']}")
    return "\n\n".join(parts)
