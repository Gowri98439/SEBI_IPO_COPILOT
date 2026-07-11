# Known Limitations

While the IPO Copilot AI platform has been production-hardened and is highly stable, there are a few theoretical constraints that remain by design or architecture choices:

1. **Local File Storage Constraints**
   - Files are currently stored on the local disk inside the configured `UPLOAD_DIR`. For a multi-node production deployment, this needs to be moved to an Object Storage bucket (like AWS S3 or Azure Blob Storage) to prevent file-not-found errors across load-balanced nodes.

2. **ChromaDB Scale**
   - We are currently using ChromaDB with local persistence. While it works phenomenally well for small to medium sets of SEBI documents and workspace uploads, Enterprise-scale multi-tenant deployments with millions of vectorized pages may require a distributed vector database like Pinecone, Milvus, or Qdrant.

3. **Rate Limits**
   - We do not currently enforce strict rate-limiting on LLM triggers (like the compliance check or document validation). A single malicious user uploading a 500-page document and triggering multiple compliance evaluations could spike API costs. A rate limiter (e.g., using Redis) is recommended before public launch.

4. **SSE (Server-Sent Events) Keep-Alives**
   - The Copilot chat stream utilizes SSE. While it is stable, certain enterprise firewalls may drop long-running HTTP connections. A WebSocket connection could be slightly more resilient if users frequently experience dropped chat completions behind strict proxies.

5. **Advanced Complex Tables in PDFs**
   - The document extraction logic uses standard unstructured parsers. Very dense financial tables may occasionally lose structural formatting when converted to text for the RAG pipeline. Using specialized OCR tabular extraction could improve accuracy for complex financial statements.
