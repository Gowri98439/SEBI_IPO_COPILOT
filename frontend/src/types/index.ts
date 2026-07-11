/* ─── User & Auth ──────────────────────────────────────────────────────── */
export interface User {
  id: string
  email: string
  full_name: string
  role: string
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

/* ─── Company ──────────────────────────────────────────────────────────── */
export interface Company {
  id: string
  name: string
  cin: string
  pan: string
  industry: string
  created_at: string
}

export interface CreateCompanyRequest {
  name: string
  cin: string
  pan: string
  industry: string
}

/* ─── Workspace ────────────────────────────────────────────────────────── */
export interface Workspace {
  id: string
  company_id: string
  name: string
  status: string
  created_at: string
}

export interface CreateWorkspaceRequest {
  company_id: string
  name: string
}

/* ─── Document ─────────────────────────────────────────────────────────── */
export interface Document {
  id: string
  workspace_id: string
  name: string
  doc_type: string
  file_size: number
  mime_type: string
  status: string
  created_at: string
}

export interface DocumentVersion {
  id: string
  document_id: string
  version_number: number
  file_path: string
  change_summary: string
  file_size?: number
  created_at: string
  created_by: string
}

/* ─── Validation ───────────────────────────────────────────────────────── */
export interface ValidationIssue {
  type: string
  severity: 'high' | 'medium' | 'low'
  description: string
  page: number
  rule: string
}

export interface MissingInfo {
  field: string
  section: string
  required_by: string
  description: string
}

export interface ValidationResult {
  id: string
  document_id: string
  status: string
  issues: ValidationIssue[]
  missing_info: MissingInfo[]
  summary: string
  created_at: string
}

/* ─── Compliance ───────────────────────────────────────────────────────── */
export interface ComplianceCheck {
  id: string
  workspace_id: string
  check_type: string
  regulation: string
  status: 'pass' | 'fail' | 'warning' | 'pending'
  evidence: Record<string, unknown>
  ai_reasoning: string
  created_at: string
}

/* ─── Copilot ──────────────────────────────────────────────────────────── */
export interface CopilotSession {
  id: string
  workspace_id: string
  user_id: string
  created_at: string
}

export interface CopilotMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  action_type?: string
  created_at: string
}

export interface SendMessageRequest {
  content: string
  action_type?: string
}

/* ─── Draft Review ─────────────────────────────────────────────────────── */
export interface DraftFeedback {
  issue: string
  suggestion: string
  severity: string
  ref_rule: string
}

export interface DraftReview {
  id: string
  workspace_id: string
  section: string
  draft_content: string
  ai_feedback: DraftFeedback[]
  status: string
  created_at: string
}

export interface CreateDraftReviewRequest {
  workspace_id: string
  section: string
  draft_content: string
}

/* ─── Human Review ─────────────────────────────────────────────────────── */
export interface ReviewTask {
  id: string
  workspace_id: string
  assigned_to: string
  task_type: string
  status: string
  notes: string
  due_date: string
  created_at: string
}

export interface CreateReviewTaskRequest {
  workspace_id: string
  assigned_to: string
  task_type: string
  notes?: string
  due_date?: string
}

/* ─── Dashboard & Audit ────────────────────────────────────────────────── */
export interface AuditEvent {
  id: string
  action: string
  status: string
  user_id?: string
  created_at: string
}
export interface DashboardStats {
  readiness_score: number
  documents_uploaded: number
  documents_required: number
  compliance_passing: number
  compliance_total: number
  pending_reviews: number
  open_issues: number
  warnings: number
  audit_events?: AuditEvent[]
}

export interface ReadinessHistory {
  date: string
  score: number
}

/* ─── API Response ─────────────────────────────────────────────────────── */
export interface ApiResponse<T> {
  success: boolean
  data: T
  meta?: {
    page: number
    total: number
    per_page?: number
  }
  error?: {
    code: string
    message: string
    details?: Record<string, string[]>
  }
}

export interface PaginationParams {
  page?: number
  per_page?: number
}

/* ─── Misc ─────────────────────────────────────────────────────────────── */
export type Severity = 'high' | 'medium' | 'low'
export type ComplianceStatus = 'pass' | 'fail' | 'warning' | 'pending'
export type DocumentStatus = 'pending' | 'uploaded' | 'validating' | 'validated' | 'failed'
export type WorkspaceStatus = 'active' | 'draft' | 'submitted' | 'approved'
