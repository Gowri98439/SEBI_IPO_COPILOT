import asyncio
from app.database import async_session_factory
from app.models.document import Document
from sqlalchemy import select
from app.ai.background_tasks import run_document_validation_task
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    async with async_session_factory() as session:
        stmt = select(Document).limit(1)
        doc = (await session.execute(stmt)).scalars().first()
        if not doc:
            print("No documents found in DB to test.")
            return
        print(f"Testing doc: {doc.id} ({doc.name})")
        print("1. Verify the Validate button sends the correct API request -> simulating via function call.")
        print("2. Verify the backend endpoint is actually called -> simulating via function call.")
        print("3. Verify the endpoint launches the background task -> directly launching background task.")
        try:
            await run_document_validation_task(str(doc.id), doc.file_path, doc.doc_type)
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
