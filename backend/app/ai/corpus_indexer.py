"""
SEBI corpus indexer for IPO Copilot.
Reads text files from the sebi_corpus directory, splits into chunks,
embeds them, and stores in ChromaDB. Called at FastAPI startup.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.ai.vector_store import (
    SEBI_COLLECTION,
    add_documents_to_vectorstore,
    get_collection_count,
)

logger = logging.getLogger(__name__)

# Path to the corpus directory (sibling of this file)
CORPUS_DIR = Path(__file__).parent / "sebi_corpus"

# Chunking configuration
CHUNK_SIZE = 512       # characters per chunk
CHUNK_OVERLAP = 64     # overlap between consecutive chunks

DRHP_HEADERS = [
    "DEFINITIONS AND ABBREVIATIONS",
    "CERTAIN CONVENTIONS, PRESENTATION OF FINANCIAL, INDUSTRY AND MARKET DATA",
    "FORWARD-LOOKING STATEMENTS",
    "RISK FACTORS",
    "INTRODUCTION",
    "GENERAL INFORMATION",
    "CAPITAL STRUCTURE",
    "OBJECTS OF THE ISSUE",
    "BASIS FOR ISSUE PRICE",
    "STATEMENT OF TAX BENEFITS",
    "INDUSTRY OVERVIEW",
    "OUR BUSINESS",
    "KEY REGULATIONS AND POLICIES",
    "HISTORY AND CERTAIN CORPORATE MATTERS",
    "OUR MANAGEMENT",
    "OUR PROMOTERS AND PROMOTER GROUP",
    "DIVIDEND POLICY",
    "FINANCIAL STATEMENTS"
]

# Mapping of filename → source label
CORPUS_FILES: dict[str, dict] = {
    "icdr_regulations.txt": {
        "source_label": "SEBI ICDR Regulations 2018",
        "source_file": "icdr_regulations.txt",
        "doc_type": "regulation",
    },
    "lodr_regulations.txt": {
        "source_label": "SEBI LODR Regulations 2015",
        "source_file": "lodr_regulations.txt",
        "doc_type": "regulation",
    },
    "sme_ipo_guidelines.txt": {
        "source_label": "NSE Emerge & BSE SME Platform Guidelines",
        "source_file": "sme_ipo_guidelines.txt",
        "doc_type": "guideline",
    },
    # ── 2024-2026 Amendments & Circulars ────────────────────────────────
    "sebi_2026_amendments.txt": {
        "source_label": "SEBI ICDR Amendments 2024-2026 (SME IPO)",
        "source_file": "sebi_2026_amendments.txt",
        "doc_type": "regulation",
    },
    "sebi_circular_2026.txt": {
        "source_label": "SEBI Circulars 2024-2026",
        "source_file": "sebi_circular_2026.txt",
        "doc_type": "circular",
    },
    # ── DRHP Training Corpus ─────────────────────────────────────────────
    "drhp_risk_factors.txt": {
        "source_label": "DRHP Risk Factors Templates by Sector",
        "source_file": "drhp_risk_factors.txt",
        "doc_type": "drhp_template",
    },
    "drhp_financial_statements.txt": {
        "source_label": "Financial Statement Analysis for DRHP — Ind AS",
        "source_file": "drhp_financial_statements.txt",
        "doc_type": "drhp_template",
    },
    "drhp_business_overview.txt": {
        "source_label": "DRHP Business Overview and Industry Analysis",
        "source_file": "drhp_business_overview.txt",
        "doc_type": "drhp_template",
    },
    "sebi_case_studies.txt": {
        "source_label": "SEBI SME IPO Case Studies and Compliance Outcomes",
        "source_file": "sebi_case_studies.txt",
        "doc_type": "case_study",
    },
}

CORPUS_VERSION = "v2.1.0"  # Bump when corpus content changes to force re-index


async def is_corpus_indexed() -> bool:
    """
    Check if the SEBI corpus has already been indexed into ChromaDB.

    Returns:
        True if the collection has at least 10 documents, False otherwise.
    """
    try:
        count = get_collection_count(SEBI_COLLECTION)
        logger.info("SEBI corpus collection '%s' has %d documents.", SEBI_COLLECTION, count)
        return count >= 10
    except Exception as exc:
        logger.warning("Could not check corpus index status: %s", exc)
        return False


def _parse_regulation_id(text: str, filename: str) -> str:
    """
    Attempt to extract a regulation ID from a chunk of text.
    Looks for patterns like 'Regulation 26', 'ICDR Reg. 26', etc.
    """
    import re

    patterns = [
        r"\bRegulation\s+(\d+[A-Za-z]?(?:\(\d+\))?)",
        r"\bReg\.?\s+(\d+[A-Za-z]?)",
        r"\bICDR\s+(\d+[A-Za-z]?)",
        r"\bLODR\s+(\d+[A-Za-z]?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:300], re.IGNORECASE)
        if match:
            reg_num = match.group(1)
            if "icdr" in filename.lower():
                return f"ICDR_REG_{reg_num}"
            elif "lodr" in filename.lower():
                return f"LODR_REG_{reg_num}"
            else:
                return f"REG_{reg_num}"
    return ""


def _extract_section(text: str) -> str:
    """Extract the section heading from the start of a chunk."""
    import re

    # Look for section patterns like "26.1", "Chapter III", "Section 4"
    patterns = [
        r"^(Chapter\s+[IVXLC]+[^\n]*)",
        r"^(Section\s+\d+[^\n]*)",
        r"^(\d+\.\d+[^\n]*)",
        r"^(Regulation\s+\d+[^\n]*)",
    ]
    for pattern in patterns:
        match = re.match(pattern, text.strip(), re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)[:120].strip()
    # Fallback: first line
    first_line = text.strip().split("\n")[0]
    return first_line[:120].strip()


def _split_by_sections(text: str) -> list[tuple[str, str]]:
    """Splits text into sections based on known DRHP headers."""
    import re
    escaped_headers = [re.escape(h) for h in DRHP_HEADERS]
    pattern = r"^(?:" + "|".join(escaped_headers) + r")"
    
    lines = text.split('\n')
    sections = []
    current_section = "General"
    current_content = []
    
    for line in lines:
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            if current_content:
                sections.append((current_section, "\n".join(current_content)))
            current_section = match.group(0).upper()
            current_content = [line]
        else:
            current_content.append(line)
            
    if current_content:
        sections.append((current_section, "\n".join(current_content)))
        
    return sections


def _load_and_chunk_file(filepath: Path, file_meta: dict) -> list[Document]:
    """
    Load a corpus text file and split it into LangChain Document chunks.

    Args:
        filepath: Absolute path to the text file.
        file_meta: Metadata dict with source_label, source_file, doc_type.

    Returns:
        List of LangChain Document objects with metadata.
    """
    if not filepath.exists():
        logger.warning("Corpus file not found: %s", filepath)
        return []

    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.error("Failed to read corpus file '%s': %s", filepath, exc)
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=False,
    )
    
    sections = _split_by_sections(text)

    documents = []
    chunk_index = 0
    for section_name, section_content in sections:
        chunks = splitter.split_text(section_content)
        for chunk in chunks:
            regulation_id = _parse_regulation_id(chunk, filepath.name)
            section_meta = section_name if section_name in DRHP_HEADERS else _extract_section(chunk)
            
            doc = Document(
                page_content=chunk,
                metadata={
                    "source_file": file_meta["source_file"],
                    "source_label": file_meta["source_label"],
                    "doc_type": file_meta["doc_type"],
                    "chunk_index": chunk_index,
                    "total_chunks": 0,
                    "regulation_id": regulation_id,
                    "section": section_meta,
                    "chapter": "",
                    "corpus_version_id": CORPUS_VERSION,
                },
            )
            documents.append(doc)
            chunk_index += 1
            
    for doc in documents:
        doc.metadata["total_chunks"] = len(documents)

    logger.info("Chunked '%s' into %d documents.", filepath.name, len(documents))
    return documents


async def index_sebi_corpus(force_reindex: bool = False) -> dict:
    """
    Index the SEBI corpus into ChromaDB.
    Called at FastAPI startup if the collection is empty (or force_reindex=True).

    Args:
        force_reindex: If True, re-index even if collection already has data.

    Returns:
        Dict with 'status', 'total_docs', and 'files_processed'.
    """
    if not force_reindex and await is_corpus_indexed():
        logger.info("SEBI corpus already indexed — skipping indexing.")
        return {
            "status": "already_indexed",
            "total_docs": get_collection_count(SEBI_COLLECTION),
            "files_processed": 0,
        }

    if not CORPUS_DIR.exists():
        logger.error("Corpus directory not found: %s", CORPUS_DIR)
        return {
            "status": "error",
            "error": f"Corpus directory not found: {CORPUS_DIR}",
            "total_docs": 0,
            "files_processed": 0,
        }

    logger.info("Starting SEBI corpus indexing from: %s", CORPUS_DIR)
    all_documents: list[Document] = []
    files_processed = 0

    for filename, meta in CORPUS_FILES.items():
        filepath = CORPUS_DIR / filename
        docs = _load_and_chunk_file(filepath, meta)
        if docs:
            all_documents.extend(docs)
            files_processed += 1

    # Also pick up any additional .txt files in corpus dir
    for txt_file in CORPUS_DIR.glob("*.txt"):
        if txt_file.name not in CORPUS_FILES:
            logger.info("Found additional corpus file: %s", txt_file.name)
            extra_meta = {
                "source_label": txt_file.stem.replace("_", " ").title(),
                "source_file": txt_file.name,
                "doc_type": "guideline",
            }
            docs = _load_and_chunk_file(txt_file, extra_meta)
            if docs:
                all_documents.extend(docs)
                files_processed += 1

    if not all_documents:
        logger.error("No documents loaded from corpus directory.")
        return {
            "status": "error",
            "error": "No documents could be loaded from the corpus directory.",
            "total_docs": 0,
            "files_processed": 0,
        }

    logger.info("Indexing %d total chunks from %d files into ChromaDB...", len(all_documents), files_processed)
    added = add_documents_to_vectorstore(all_documents, SEBI_COLLECTION)
    logger.info("Corpus indexing complete. Added %d documents.", added)

    return {
        "status": "indexed",
        "total_docs": added,
        "files_processed": files_processed,
    }


async def index_single_file(
    filepath: str | Path,
    source_label: str,
    doc_type: str = "regulation",
) -> int:
    """
    Index a single additional text file into the SEBI corpus.
    Useful for adding custom regulatory documents.

    Args:
        filepath: Path to the text file.
        source_label: Human-readable label for the source.
        doc_type: Type of document ('regulation', 'guideline', 'circular').

    Returns:
        Number of chunks indexed.
    """
    filepath = Path(filepath)
    meta = {
        "source_label": source_label,
        "source_file": filepath.name,
        "doc_type": doc_type,
    }
    docs = _load_and_chunk_file(filepath, meta)
    if not docs:
        return 0
    return add_documents_to_vectorstore(docs, SEBI_COLLECTION)
