"""
File upload validator — permissive and Windows-compatible.
Accepts PDF, DOCX, DOC, XLSX, XLS, CSV.
"""
import uuid
from pathlib import Path
from fastapi import HTTPException, status

# Allowed MIME types (magic-detected or content-type header)
ALLOWED_MIMES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/octet-stream",   # many browsers send this for all files
    "application/zip",            # DOCX/XLSX are zip-based
}

# Allowed extensions → forced extension in safe filename
EXT_MAP = {
    ".pdf": ".pdf",
    ".doc": ".doc",
    ".docx": ".docx",
    ".xls": ".xls",
    ".xlsx": ".xlsx",
    ".csv": ".csv",
}

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def validate_upload(file_content: bytes, original_filename: str) -> str:
    """
    Validate uploaded file and return a UUID-based safe filename.
    Raises HTTPException on failure.
    """
    # 1. Size check
    if len(file_content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 50 MB.",
        )

    # 2. Extension check (primary guard on Windows where libmagic may not be reliable)
    suffix = Path(original_filename).suffix.lower()
    if suffix not in EXT_MAP:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{suffix}' is not supported. Accepted: PDF, DOC, DOCX, XLS, XLSX, CSV.",
        )

    # 3. PDF-specific header magic bytes check (fast, no library needed)
    if suffix == ".pdf":
        if not file_content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded file does not appear to be a valid PDF document.",
            )

    # 4. Minimum size check (avoid empty files)
    if len(file_content) < 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file appears to be empty.",
        )

    # 5. Generate safe UUID filename preserving extension
    safe_ext = EXT_MAP[suffix]
    safe_filename = f"{uuid.uuid4()}{safe_ext}"
    return safe_filename
