import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> dict[str, str]:
    """
    Extract text from each page of a PDF using PyMuPDF (fitz).
    Returns a dict mapping page number (str) to page text.
    """
    try:
        import fitz  # PyMuPDF

        result: dict[str, str] = {}
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc, start=1):  # type: ignore
                text = page.get_text("text")
                result[str(page_num)] = text
        return result
    except Exception as exc:
        logger.error("Failed to extract text from PDF %s: %s", file_path, exc)
        return {}


def extract_tables_from_pdf(file_path: str) -> list[dict[str, Any]]:
    """
    Extract tables from a PDF using pdfplumber.
    Returns a list of dicts: {page: int, table: list[list]}.
    """
    try:
        import pdfplumber

        results: list[dict[str, Any]] = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        results.append({"page": page_num, "table": table})
        return results
    except Exception as exc:
        logger.error("Failed to extract tables from PDF %s: %s", file_path, exc)
        return []


def get_full_text(file_path: str) -> str:
    """
    Return all text from a PDF concatenated with page markers.
    """
    pages = extract_text_from_pdf(file_path)
    if not pages:
        return ""
    parts: list[str] = []
    for page_num in sorted(pages.keys(), key=int):
        parts.append(f"--- Page {page_num} ---\n{pages[page_num]}")
    return "\n\n".join(parts)
