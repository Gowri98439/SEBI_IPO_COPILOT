"""
Document Intelligence Engine for processing and indexing uploaded workspace documents.
Implements OCR (if required), text/table extraction, classification, metadata extraction,
chunking, embedding, and indexing into ChromaDB for Hybrid RAG.
"""
from __future__ import annotations

import logging
import uuid
import pdfplumber
from datetime import datetime, timezone
from langchain_core.documents import Document as LangchainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.vector_store import get_workspace_vectorstore, add_documents_to_vectorstore

logger = logging.getLogger(__name__)

def parse_pdf_for_indexing(
    file_path: str,
    document_id: str,
    workspace_id: str,
    doc_type: str,
    company_id: str = "unknown",
    version: str = "1"
) -> list[LangchainDocument]:
    """
    Extracts text and tables from PDF, preserving page numbers and adding metadata.
    """
    documents: list[LangchainDocument] = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                
                # 1. Extract Text
                text = page.extract_text() or ""
                
                # 2. Extract Tables (basic markdown conversion for LLM readability)
                tables = page.extract_tables()
                table_text = ""
                for table in tables:
                    if table:
                        for row in table:
                            # Clean up None values in rows
                            clean_row = [str(cell).replace("\n", " ") if cell else "" for cell in row]
                            table_text += " | ".join(clean_row) + "\n"
                        table_text += "\n"
                        
                full_page_content = text
                if table_text:
                    full_page_content += "\n[Extracted Tables]:\n" + table_text

                if not full_page_content.strip():
                    continue

                # 3. Metadata Extraction & Classification
                # Attempt to determine section/chapter based on heuristics if possible
                # (For now, we store basic metadata as requested in Phase 2)
                metadata = {
                    "document_id": str(document_id),
                    "workspace_id": str(workspace_id),
                    "document_version": version,
                    "document_type": doc_type,
                    "company_id": company_id,
                    "page_number": str(page_num),
                    "section": "unknown",  # Could be enhanced with regex header matching
                    "chapter": "unknown",
                    "source": f"{file_path} - Page {page_num}",
                    "effective_date": datetime.now(timezone.utc).isoformat(),
                    "regulation_id": "", # To be filled during compliance check matching if needed
                }
                
                documents.append(
                    LangchainDocument(page_content=full_page_content, metadata=metadata)
                )
                
        logger.info(
            "Document Intelligence: Extracted %d pages from %s (doc_id=%s)",
            total_pages, file_path, document_id
        )
    except Exception as exc:
        logger.error("Failed to parse PDF '%s': %s", file_path, exc, exc_info=True)
        
    return documents


async def index_workspace_document(
    file_path: str,
    document_id: str,
    workspace_id: str,
    doc_type: str,
    company_id: str = "unknown"
) -> int:
    """
    Main pipeline: OCR/Extract -> Chunking -> Embedding -> Indexing
    """
    # 1. Extraction (Text + Tables + Page Detection)
    import asyncio
    raw_docs = await asyncio.to_thread(
        parse_pdf_for_indexing,
        file_path=file_path,
        document_id=document_id,
        workspace_id=workspace_id,
        doc_type=doc_type,
        company_id=company_id
    )
    
    if not raw_docs:
        logger.warning("No indexable text found for document_id=%s", document_id)
        return 0

    # 2. Chunking
    # We use a RecursiveCharacterTextSplitter to ensure we don't exceed token limits
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunked_docs = splitter.split_documents(raw_docs)
    
    # 3 & 4. Embedding and Indexing
    # We prefix the collection name with 'workspace_' to keep it separate from SEBI corpus
    collection_name = f"workspace_{workspace_id}"
    
    # Add documents asynchronously using our vector_store helper
    added_count = await asyncio.to_thread(
        add_documents_to_vectorstore,
        chunked_docs,
        collection_name
    )
    
    logger.info(
        "Document Intelligence: Indexed %d chunks into %s for document_id=%s",
        added_count, collection_name, document_id
    )
    return added_count
