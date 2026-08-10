# Data Model & Schema Definition
*Phase 0 Deliverable*

## 1. Existing SQLAlchemy Models
Located in `backend/app/models/`:

### 1.1 User & Auth
- `User`: id, email, password_hash, full_name, role, created_at, updated_at
- `RefreshToken`: token tracking for secure sessions.
- `TokenBlacklist`: revoked JWTs.

### 1.2 Core Domain
- `Workspace`: multi-tenant boundary (id, name, owner_id).
- `Company`: target IPO entity (id, workspace_id, cin, name).
- `Document`: uploaded files (id, workspace_id, filename, status).
- `Version` & `CorpusVersion`: document versioning.

### 1.3 Assessment & AI
- `ComplianceCheck`: results of basic compliance checks.
- `ValidationResult`: financial validation state.
- `Copilot`: chat session state.
- `Review` & `AuditEvent`: rudimentary logging.

## 2. Planned Models (Government-Grade Upgrade)
To support the Evidence/Audit/Risk requirements, the following models will be introduced via Alembic migrations in Phase 1:

### 2.1 Evidence & Traceability
- **`EvidenceRecord`**: 
  - `id`, `claim_text`, `source_document_id`, `document_version`, `page_number`, `source_text`, `regulation_id`, `verification_status`, `reviewer_id`.
- **`RegulationVersion`**: 
  - `id`, `regulation_code`, `version_tag`, `effective_date`, `superseded_date`.

### 2.2 Compliance & Risk
- **`ComplianceFinding`**: 
  - `id`, `rule_id`, `regulation_version_id`, `status` (PASS/FAIL/PARTIAL/MISSING/REQUIRES REVIEW), `evidence_id`, `reviewer_decision`.
- **`RiskFinding`**: 
  - `id`, `category` (Financial/Legal/Governance/Business), `severity` (LOW/MEDIUM/HIGH/CRITICAL), `evidence_id`, `description`.

### 2.3 Workflow & Audit
- **`WorkflowState`**: 
  - Tracks transition of a Workspace/Company (Submission → Screening → AI Analysis → Human Review → Approved).
- **`AuditEvent` (V2)**: 
  - `id`, `actor_id`, `role`, `action`, `object_type`, `object_id`, `previous_state`, `new_state`, `reason`, `timestamp`.

### 2.4 Intelligence
- **`HistoricalIPO`**: 
  - `id`, `company_name`, `sector`, `issue_size_cr`, `revenue_cr`, `pat_margin`, `listing_performance`, `is_verified` (Boolean - strictly separates real from synthetic data).
- **`AIExecution`**:
  - `id`, `job_id`, `model_name`, `prompt_version`, `timestamp`, `token_usage`.
