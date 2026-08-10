# Security Audit Report
*Phase 0 Deliverable*

## 1. Authentication & Identity
- **Current State**: JWT-based authentication is implemented with `access_token` and `refresh_token`. Token revocation (blacklist) is present.
- **Risk Level**: Low.
- **Required Action**: Ensure all endpoints require the `get_current_user` dependency.

## 2. Authorization & RBAC
- **Current State**: Basic role definition (`analyst`), but no robust Role-Based Access Control (RBAC) middleware.
- **Risk Level**: High.
- **Required Action**: 
  - Define strict roles: `Administrator`, `Regulatory Officer`, `Reviewer`, `Merchant Banker`, `Company User`.
  - Implement `@require_role(...)` decorators for sensitive endpoints.

## 3. Data Isolation (Workspace / Tenant Isolation)
- **Current State**: Workspace ID is used, but physical tenant isolation at the ORM/Query layer is likely not enforced via a global interceptor.
- **Risk Level**: High (IDOR Vulnerability risk).
- **Required Action**: 
  - Audit all `GET`, `PUT`, `DELETE` endpoints to ensure `where(workspace_id == current_user.workspace_id)`.
  - Test explicit cross-tenant unauthorized access in Phase 23.

## 4. Prompt Injection & AI Safety
- **Current State**: Standard LLM calls via LangChain. System prompts are rigid, but user input might bypass them.
- **Risk Level**: Medium.
- **Required Action**: 
  - Implement Input Validation on all `DrhpRequestV2` fields.
  - Rate limiting on Copilot chat endpoints.

## 5. File Processing Security
- **Current State**: File uploads accepted for RAG processing.
- **Risk Level**: Medium.
- **Required Action**: 
  - Restrict MIME types strictly (PDF, DOCX).
  - Implement secure file storage and filename sanitization.
  - Sandbox or tightly control the PyMuPDF parsing to prevent malicious PDF execution.

## 6. Audit Logging Integrity
- **Current State**: `AuditEvent` model exists but is not immutable.
- **Risk Level**: Medium.
- **Required Action**: 
  - Prevent `UPDATE` or `DELETE` operations on the `audit_events` table at the DB user level.
  - Ensure every state transition logs the Actor and Timestamp.
