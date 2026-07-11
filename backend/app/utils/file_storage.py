import os
import uuid

import aiofiles
from fastapi import UploadFile

from app.config import settings


def _ensure_upload_dir(workspace_id: str) -> str:
    dir_path = os.path.join(settings.UPLOAD_DIR, workspace_id)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


async def save_upload(file: UploadFile, workspace_id: str, safe_filename: str | None = None) -> tuple[str, int]:
    """Save an uploaded file and return (relative_path, file_size_bytes)."""
    dir_path = _ensure_upload_dir(workspace_id)
    
    unique_name = safe_filename if safe_filename else f"{uuid.uuid4()}.pdf"
    abs_path = os.path.join(dir_path, unique_name)
    
    # Ensure the resolved path is still inside the upload directory
    if not os.path.abspath(abs_path).startswith(os.path.abspath(settings.UPLOAD_DIR)):
        raise ValueError("Invalid file path detected.")
        
    relative_path = os.path.join(workspace_id, unique_name)

    content = await file.read()
    async with aiofiles.open(abs_path, "wb") as out_file:
        await out_file.write(content)

    return relative_path, len(content)


def get_file_path(relative_path: str) -> str:
    """Return the absolute path for a stored relative path."""
    # If the relative path already starts with 'uploads/', remove it to prevent 'uploads/uploads/'
    if relative_path.startswith("uploads/"):
        relative_path = relative_path[8:]
    elif relative_path.startswith("uploads\\"):
        relative_path = relative_path[8:]
        
    abs_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, relative_path))
    # Security: Ensure we don't traverse outside UPLOAD_DIR
    if not abs_path.startswith(os.path.abspath(settings.UPLOAD_DIR)):
        raise ValueError("Invalid file path detected.")
    return abs_path


def delete_file(relative_path: str) -> None:
    """Delete a file from storage. Silently ignores missing files."""
    try:
        abs_path = get_file_path(relative_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass
