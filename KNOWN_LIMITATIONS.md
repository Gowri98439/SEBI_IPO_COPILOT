# Known Limitations

This document accurately reflects known gaps and trade-offs in the current IPO Copilot AI implementation.

1. **Local File Storage**
   - Files are stored on the local disk inside `UPLOAD_DIR`. Multi-node production deployments require migration to Object Storage (AWS S3, Azure Blob) to prevent file-not-found errors across load-balanced nodes.

2. **ChromaDB Scale**
   - ChromaDB with local persistence is used. Works well for small-medium document sets. Enterprise-scale multi-tenant deployments with millions of vectorized pages would require a distributed vector database (Pinecone, Milvus, Qdrant).

3. **Rate Limiting**
   - `@limiter.limit()` decorators are applied to the compliance check, copilot message, and document upload endpoints. However, a compliance check triggers up to 30 parallel LLM calls — even with `10/minute` rate limiting, this could generate 300 LLM calls/minute for a single user. Redis-backed rate limiting with token-bucket semantics is recommended before public launch.

4. **No Automated Tests**
   - There are currently no `pytest` unit or integration tests. All test scripts in the repository (`test_*.py`) are manual smoke scripts making live HTTP calls. Adding a real test suite is the highest-priority engineering debt before production.

5. **Scanned (Image) PDFs — Not Supported**
   - The document extraction pipeline only processes text-native PDFs. Scanned (image-based) PDFs are detected and return an explicit error message, but are **not processed via OCR**. This affects older SME filings that are image-only. `pytesseract` or a cloud OCR API integration is required to support this use case.

6. **Background Job Resilience**
   - Background tasks use FastAPI's built-in `BackgroundTasks` (in-process). A server restart mid-run will leave compliance check records in `pending` status permanently. A real task queue (Celery/arq + Redis) with retry logic and startup reconciliation is needed for production reliability.

7. **SSE Keep-Alives**
   - The Copilot chat stream uses SSE. Certain enterprise firewalls may drop long-running HTTP connections. A WebSocket upgrade would be more resilient for users behind strict proxies.
