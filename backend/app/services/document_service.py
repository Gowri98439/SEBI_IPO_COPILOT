import uuid
from uuid import UUID
import os
import aiofiles

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.validation_result import ValidationResult
from app.models.version import DocumentVersion
from app.utils.file_storage import save_upload
from app.config import settings


class DocumentService:
    @staticmethod
    async def upload_from_bytes(
        db: AsyncSession,
        workspace_id: str,
        file_content: bytes,
        original_filename: str,
        content_type: str | None,
        doc_type: str | None,
        user_id: str,
        safe_filename: str | None = None,
    ) -> Document:
        """Save file bytes to disk and create/update the Document DB record."""
        # Save to disk
        dir_path = os.path.join(settings.UPLOAD_DIR, workspace_id)
        os.makedirs(dir_path, exist_ok=True)
        fname = safe_filename or f"{uuid.uuid4()}.pdf"
        abs_path = os.path.join(dir_path, fname)
        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(file_content)
        relative_path = os.path.join(workspace_id, fname)
        file_size = len(file_content)

        # Check if document with same name already exists
        result = await db.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.name == original_filename,
            )
        )
        existing_doc = result.scalars().first()

        if existing_doc:
            existing_doc.file_path = relative_path  # type: ignore
            existing_doc.file_size = file_size  # type: ignore
            existing_doc.mime_type = content_type  # type: ignore
            existing_doc.status = "uploaded"  # type: ignore
            existing_doc.uploaded_by = user_id  # type: ignore
            if doc_type:
                existing_doc.doc_type = doc_type  # type: ignore
            db.add(existing_doc)
            version_result = await db.execute(
                select(DocumentVersion.version_number)
                .where(DocumentVersion.document_id == existing_doc.id)
                .order_by(DocumentVersion.version_number.desc())
                .limit(1)
            )
            max_version = version_result.scalars().first() or 0
            version = DocumentVersion(
                document_id=existing_doc.id,
                version_number=max_version + 1,
                file_path=relative_path,
                change_summary=f"Updated to version {max_version + 1}",
                created_by=user_id,
            )
            db.add(version)
            doc = existing_doc
        else:
            doc = Document(
                workspace_id=workspace_id,
                name=original_filename,
                doc_type=doc_type,
                file_path=relative_path,
                file_size=file_size,
                mime_type=content_type,
                status="uploaded",
                uploaded_by=user_id,
            )
            db.add(doc)
            await db.flush()
            await db.refresh(doc)
            version = DocumentVersion(
                document_id=doc.id,
                version_number=1,
                file_path=relative_path,
                change_summary="Initial upload",
                created_by=user_id,
            )
            db.add(version)

        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def list_documents(db: AsyncSession, workspace_id: str) -> list[Document]:

        result = await db.execute(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_document(db: AsyncSession, doc_id: str) -> Document:
        result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )
        return doc

    @staticmethod
    async def trigger_validation(
        db: AsyncSession, doc_id: str
    ) -> ValidationResult:
        # Ensure document exists
        result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Create a pending validation result
        validation = ValidationResult(
            document_id=doc.id,
            status="pending",
            issues=[],
            missing_info=[],
            summary=None,
        )
        db.add(validation)
        await db.flush()
        await db.refresh(validation)

        # Update document status
        doc.status = "validating"  # type: ignore
        db.add(doc)
        await db.flush()
        return validation

    @staticmethod
    async def get_validation_result(
        db: AsyncSession, doc_id: str
    ) -> ValidationResult | None:
        result = await db.execute(
            select(ValidationResult)
            .where(ValidationResult.document_id == doc_id)
            .order_by(ValidationResult.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def get_versions(
        db: AsyncSession, doc_id: str
    ) -> list[DocumentVersion]:
        result = await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc_id)
            .order_by(DocumentVersion.version_number.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def soft_delete(db: AsyncSession, doc_id: str) -> Document:
        doc = await DocumentService.get_document(db, doc_id)
        doc.status = "deleted"  # type: ignore
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return doc
