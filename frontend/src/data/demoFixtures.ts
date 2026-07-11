/**
 * Demo Mode fixtures — Pinnacle Micro Industries Limited
 * A fictional SME preparing for BSE SME IPO.
 * These fixtures are used when isDemoMode is true.
 */

const WORKSPACE_ID = 'demo-workspace-001'
const USER_ID = 'demo-user-001'

/* ─── Documents ─────────────────────────────────────────────────────────── */
export const DEMO_DOCUMENTS = [
  {
    id: 'demo-doc-drhp',
    workspace_id: WORKSPACE_ID,
    name: 'DRHP_Pinnacle_Micro_v3.pdf',
    doc_type: 'prospectus_draft',
    file_size: 2456000,
    status: 'validated',
    created_at: '2026-07-04T09:15:00Z',
  },
  {
    id: 'demo-doc-financials',
    workspace_id: WORKSPACE_ID,
    name: 'Restated_Financials_FY24-26.pdf',
    doc_type: 'financial_statement',
    file_size: 3180000,
    status: 'validated',
    created_at: '2026-07-04T09:22:00Z',
  },
  {
    id: 'demo-doc-auditor',
    workspace_id: WORKSPACE_ID,
    name: 'Auditor_Report_Pinnacle.pdf',
    doc_type: 'auditor_report',
    file_size: 890000,
    status: 'validated',
    created_at: '2026-07-04T09:30:00Z',
  },
]

/* ─── Validation Results ────────────────────────────────────────────────── */
export const DEMO_VALIDATION_RESULTS: Record<string, any> = {
  'demo-doc-drhp': {
    status: 'completed',
    summary: 'DRHP draft reviewed against SEBI ICDR 2018 requirements for SME IPO. 3 critical issues and 4 warnings identified. Promoter contribution section requires immediate attention.',
    issues: [
      {
        description: 'Promoter contribution of 18.5% is below the mandatory 20% minimum under ICDR Regulation 26',
        rule: 'ICDR_REG_26',
        severity: 'high',
        page: 42,
      },
      {
        description: 'Lock-in period for minimum promoters contribution not clearly stated as 3 years',
        rule: 'ICDR_REG_16',
        severity: 'high',
        page: 44,
      },
      {
        description: 'Objects of the issue section does not include deployment schedule as required',
        rule: 'ICDR_REG_32',
        severity: 'high',
        page: 28,
      },
      {
        description: 'Risk factors section contains generic industry risks without company-specific analysis',
        rule: 'ICDR_REG_57',
        severity: 'medium',
        page: 12,
      },
      {
        description: 'Related party transactions disclosure incomplete — missing transactions with promoter group entities',
        rule: 'ICDR_REG_34',
        severity: 'medium',
        page: 67,
      },
      {
        description: 'Restated financial statements reference FY2024 but latest available is FY2023',
        rule: 'ICDR_REG_26',
        severity: 'medium',
        page: 55,
      },
      {
        description: 'Capitalization statement not updated to reflect latest audited figures',
        rule: 'ICDR_REG_30',
        severity: 'medium',
        page: 38,
      },
    ],
    missing_info: [
      { field: 'Weighted Average Price', section: 'Capital Structure', required_by: 'ICDR Reg. 26(6)', description: 'Weighted average price at which equity shares were acquired in last 3 years' },
      { field: 'Deployment Schedule', section: 'Objects of Issue', required_by: 'ICDR Reg. 32', description: 'Quarter-wise fund deployment schedule' },
      { field: 'Track Record Certificate', section: 'Eligibility', required_by: 'ICDR Reg. 106(2)', description: 'Certificate from CA confirming net tangible assets and distributable profits' },
    ],
  },
}

/* ─── Compliance Checks ─────────────────────────────────────────────────── */
export const DEMO_COMPLIANCE_CHECKS = [
  // Failing checks
  {
    id: 'demo-cc-01',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_26',
    regulation: 'ICDR Regulation 26 — Minimum Promoter Contribution',
    status: 'fail',
    evidence: { evidence: 'Promoter contribution shown as 18.5% of post-issue capital in DRHP Section 4.2. SEBI requires minimum 20%.' },
    ai_reasoning: 'Promoters must contribute at least 20% of the post-issue capital. Current DRHP shows 18.5% which is 1.5% below the statutory minimum. This is a critical filing blocker.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-02',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_16',
    regulation: 'ICDR Regulation 16 — Lock-in Period',
    status: 'fail',
    evidence: { evidence: 'Lock-in clause on page 44 states "2 years" but minimum promoter contribution must be locked in for 3 years per ICDR Reg 16(1).' },
    ai_reasoning: 'The lock-in period for minimum promoters contribution is 3 years from date of allotment. DRHP incorrectly states 2 years.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-03',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_32',
    regulation: 'ICDR Regulation 32 — Objects of the Issue',
    status: 'fail',
    evidence: { evidence: 'Objects section lists 4 purposes but does not include quarter-wise deployment schedule as mandated.' },
    ai_reasoning: 'Objects of the issue must include means of financing and deployment schedule. Current draft lists objects without specifying timelines.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-04',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_57',
    regulation: 'ICDR Regulation 57 — Risk Factors',
    status: 'fail',
    evidence: { evidence: 'Risk factors on pages 12-18 include generic statements like "industry cyclicality" without company-specific risk analysis.' },
    ai_reasoning: 'Risk factors must be specific to the issuer and not generic industry risks. Several listed risks are boilerplate language.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-05',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_34',
    regulation: 'ICDR Regulation 34 — Related Party Transactions',
    status: 'fail',
    evidence: { evidence: 'Related party section omits transactions with Pinnacle Holdings Pvt. Ltd., a promoter group entity with ₹2.3Cr outstanding.' },
    ai_reasoning: 'All related party transactions must be fully disclosed per AS-18 / Ind AS 24 as required under ICDR. Missing promoter group entity transactions.',
    created_at: '2026-07-04T10:15:00Z',
  },
  // Warning checks
  {
    id: 'demo-cc-06',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_30',
    regulation: 'ICDR Regulation 30 — Capitalization Statement',
    status: 'warning',
    evidence: { evidence: 'Capitalization statement references figures as of March 2025 but audited statements are available through March 2026.' },
    ai_reasoning: 'Capitalization statement should reflect the most recent audited financial position. Current figures are one year old.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-07',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_106',
    regulation: 'ICDR Regulation 106 — SME Eligibility Track Record',
    status: 'warning',
    evidence: { evidence: 'Track record certificate from CA not found in uploaded documents. Required to confirm net tangible assets ≥ ₹1Cr.' },
    ai_reasoning: 'SME issuer must have net tangible assets of at least ₹1 crore as per last audited financial statements, certified by practicing CA.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-08',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_46',
    regulation: 'ICDR Regulation 46 — Disclosure of Group Companies',
    status: 'warning',
    evidence: { evidence: 'Group companies section lists 3 entities but does not include financial summary for each as required.' },
    ai_reasoning: 'Financial summary including turnover and net worth for each group company must be disclosed.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-09',
    workspace_id: WORKSPACE_ID,
    check_type: 'LODR_46',
    regulation: 'LODR Regulation 46 — Website Disclosures',
    status: 'warning',
    evidence: { evidence: 'Company website does not contain all mandatory disclosures required under LODR Reg 46 for listed entities.' },
    ai_reasoning: 'Post-listing, the company website must display specified information. Pre-IPO website should be prepared.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-10',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_38',
    regulation: 'ICDR Regulation 38 — Financial Statements Disclosure',
    status: 'warning',
    evidence: { evidence: 'Financial statements are restated but examination report from statutory auditor not attached.' },
    ai_reasoning: 'Restated financial statements must be accompanied by an examination report from the statutory auditor.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-11',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_48',
    regulation: 'ICDR Regulation 48 — Litigation Disclosures',
    status: 'warning',
    evidence: { evidence: 'Outstanding litigation section mentions pending tax assessment but does not quantify potential liability.' },
    ai_reasoning: 'All pending litigations must include quantification of potential financial impact where ascertainable.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-12',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_50',
    regulation: 'ICDR Regulation 50 — Management Discussion & Analysis',
    status: 'warning',
    evidence: { evidence: 'MD&A section discusses revenue growth but omits discussion of material changes in financial ratios.' },
    ai_reasoning: 'MD&A must include analysis of changes in significant financial ratios comparing recent periods.',
    created_at: '2026-07-04T10:15:00Z',
  },
  // Passing checks
  {
    id: 'demo-cc-13',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_27',
    regulation: 'ICDR Regulation 27 — Allotment Procedure',
    status: 'pass',
    evidence: { evidence: 'Allotment procedure clearly described on pages 78-80 with proportionate basis methodology.' },
    ai_reasoning: 'Allotment procedure is correctly described and compliant with ICDR requirements for SME IPO.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-14',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_28',
    regulation: 'ICDR Regulation 28 — Underwriting',
    status: 'pass',
    evidence: { evidence: 'Issue is 100% underwritten as confirmed in underwriting agreement dated June 2026.' },
    ai_reasoning: 'SME IPO is fully underwritten as required under ICDR for SME exchange listing.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-15',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_108',
    regulation: 'ICDR Regulation 108 — Market Making',
    status: 'pass',
    evidence: { evidence: 'Market maker agreement with ABC Securities for minimum 3 years post-listing documented.' },
    ai_reasoning: 'Market making arrangement is in place as required for SME exchange listing.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-16',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_29',
    regulation: 'ICDR Regulation 29 — Issue Price',
    status: 'pass',
    evidence: { evidence: 'Issue price determination methodology clearly stated with justification and comparison with peer companies.' },
    ai_reasoning: 'Price band and pricing methodology adequately disclosed.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-17',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_33',
    regulation: 'ICDR Regulation 33 — Basis for Issue Price',
    status: 'pass',
    evidence: { evidence: 'Basis for issue price section includes EPS, PE ratio, RoNW comparison with industry peers.' },
    ai_reasoning: 'Qualitative and quantitative factors for issue price basis are adequately disclosed.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-18',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_40',
    regulation: 'ICDR Regulation 40 — Promoter Background',
    status: 'pass',
    evidence: { evidence: 'Promoter and promoter group details with educational qualifications, experience, and directorships disclosed.' },
    ai_reasoning: 'Promoter background disclosure is comprehensive and compliant.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-19',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_42',
    regulation: 'ICDR Regulation 42 — Dividend Policy',
    status: 'pass',
    evidence: { evidence: 'Dividend policy section states the company has no fixed dividend policy and past dividends are disclosed.' },
    ai_reasoning: 'Dividend policy and historical dividend track record adequately disclosed.',
    created_at: '2026-07-04T10:15:00Z',
  },
  {
    id: 'demo-cc-20',
    workspace_id: WORKSPACE_ID,
    check_type: 'ICDR_44',
    regulation: 'ICDR Regulation 44 — Board of Directors',
    status: 'pass',
    evidence: { evidence: 'Board composition with independent directors meeting minimum requirements disclosed.' },
    ai_reasoning: 'Board composition complies with Companies Act and SEBI requirements.',
    created_at: '2026-07-04T10:15:00Z',
  },
]

/* ─── Dashboard Stats ───────────────────────────────────────────────────── */
export const DEMO_DASHBOARD_STATS = {
  total_documents: 3,
  validated_documents: 3,
  total_compliance_checks: 20,
  passing_checks: 8,
  failing_checks: 5,
  warning_checks: 7,
  open_issues: 5,
  warnings: 7,
  filing_readiness: 68,
}

/* ─── Audit Trail Events ────────────────────────────────────────────────── */
export const DEMO_AUDIT_EVENTS = [
  { id: 'evt-1', timestamp: '2026-07-04T09:15:00Z', type: 'human' as const, title: 'Document Uploaded', description: 'User uploaded DRHP_Pinnacle_Micro_v3.pdf' },
  { id: 'evt-2', timestamp: '2026-07-04T09:22:00Z', type: 'human' as const, title: 'Document Uploaded', description: 'User uploaded Restated_Financials_FY24-26.pdf' },
  { id: 'evt-3', timestamp: '2026-07-04T09:30:00Z', type: 'human' as const, title: 'Document Uploaded', description: 'User uploaded Auditor_Report_Pinnacle.pdf' },
  { id: 'evt-4', timestamp: '2026-07-04T10:02:00Z', type: 'ai' as const, title: 'AI Document Validation', description: 'Validated DRHP_Pinnacle_Micro_v3.pdf — 3 critical issues, 4 warnings found' },
  { id: 'evt-5', timestamp: '2026-07-04T10:08:00Z', type: 'ai' as const, title: 'AI Document Validation', description: 'Validated Restated_Financials_FY24-26.pdf — 1 warning found' },
  { id: 'evt-6', timestamp: '2026-07-04T10:12:00Z', type: 'ai' as const, title: 'AI Document Validation', description: 'Validated Auditor_Report_Pinnacle.pdf — no issues found' },
  { id: 'evt-7', timestamp: '2026-07-04T10:15:00Z', type: 'ai' as const, title: 'Compliance Engine Executed', description: 'Ran 20 SEBI compliance checks — 5 failing, 7 warnings, 8 passing' },
  { id: 'evt-8', timestamp: '2026-07-04T11:30:00Z', type: 'human' as const, title: 'Draft Submitted', description: 'User submitted Risk Factors section for AI review' },
]

/* ─── Draft Reviews ─────────────────────────────────────────────────────── */
export const DEMO_DRAFT_REVIEWS = [
  {
    id: 'demo-dr-01',
    workspace_id: WORKSPACE_ID,
    section: 'Risk Factors',
    draft_content: 'The company faces risks related to industry cyclicality, competition from larger players, dependence on key customers, and regulatory changes in the micro-electronics sector. The company\'s operations are subject to various environmental regulations.',
    status: 'reviewed',
    ai_feedback: [
      {
        issue: 'Risk factors are generic and not company-specific',
        suggestion: 'Replace "industry cyclicality" with specific quantified risks. For example: "Revenue from our top 3 customers constituted 62% of FY2026 revenue. Loss of any key customer could reduce revenue by ₹4.2Cr annually."',
        severity: 'high',
        ref_rule: 'ICDR_REG_57',
      },
      {
        issue: 'Missing quantification of regulatory risk',
        suggestion: 'Specify which environmental regulations apply, compliance costs incurred (₹X lakhs in FY2026), and potential penalties for non-compliance.',
        severity: 'medium',
        ref_rule: 'ICDR_REG_57',
      },
      {
        issue: 'No disclosure of technology obsolescence risk',
        suggestion: 'Add risk factor addressing technology lifecycle in micro-electronics and R&D expenditure (currently ₹45L or 2.1% of revenue).',
        severity: 'medium',
        ref_rule: 'ICDR_REG_57',
      },
      {
        issue: 'Risk prioritization does not follow materiality order',
        suggestion: 'SEBI guidelines require risk factors to be ordered by materiality. Customer concentration (62%) should precede generic industry risks.',
        severity: 'low',
        ref_rule: 'ICDR_REG_57',
      },
    ],
    created_at: '2026-07-04T11:30:00Z',
  },
]

/* ─── Copilot Messages ──────────────────────────────────────────────────── */
export const DEMO_COPILOT_MESSAGES = [
  {
    id: 'demo-msg-01',
    session_id: 'demo-session-01',
    role: 'user',
    content: 'Explain the minimum promoter contribution requirement for SME IPOs under ICDR.',
    created_at: '2026-07-04T12:00:00Z',
  },
  {
    id: 'demo-msg-02',
    session_id: 'demo-session-01',
    role: 'assistant',
    content: 'Under SEBI ICDR Regulation 26, promoters of an SME issuer must contribute a minimum of 20% of the post-issue capital. [ICDR_REG_26]\n\nThis contribution must be locked in for a period of 3 years from the date of allotment in the IPO, as specified under Regulation 16(1). [ICDR_REG_16]\n\nIn your current DRHP (Pinnacle Micro Industries), the promoter contribution is shown as 18.5%, which is 1.5% below the mandatory minimum. This must be rectified before filing — either by increasing the promoter contribution or restructuring the issue size.\n\nThe weighted average price of equity shares acquired by promoters in the last 3 years must also be disclosed per Regulation 26(6).',
    created_at: '2026-07-04T12:00:30Z',
  },
  {
    id: 'demo-msg-03',
    session_id: 'demo-session-01',
    role: 'user',
    content: 'What are the consequences of filing with insufficient promoter contribution?',
    created_at: '2026-07-04T12:01:00Z',
  },
  {
    id: 'demo-msg-04',
    session_id: 'demo-session-01',
    role: 'assistant',
    content: 'Filing a DRHP with insufficient promoter contribution has several consequences:\n\n1. **Rejection by SEBI**: The DRHP will be returned with observations requiring rectification. SEBI will not issue its final observations until the promoter contribution meets the 20% minimum. [ICDR_REG_26]\n\n2. **Delay in IPO timeline**: Typically adds 4-6 weeks to the filing process as the company must revise the capital structure, re-file, and await fresh SEBI observations.\n\n3. **Exchange rejection**: BSE SME exchange will independently verify promoter contribution compliance before granting in-principle listing approval. [ICDR_REG_106]\n\n4. **Merchant banker liability**: The lead merchant banker is required to certify compliance with all ICDR requirements. Filing with known non-compliance exposes the merchant banker to SEBI enforcement action.\n\nRecommendation: Increase promoter contribution from 18.5% to at least 20.5% (maintaining a buffer) before filing the revised DRHP.',
    created_at: '2026-07-04T12:01:45Z',
  },
]

export const DEMO_COPILOT_SESSIONS = [
  {
    id: 'demo-session-01',
    workspace_id: WORKSPACE_ID,
    user_id: USER_ID,
    created_at: '2026-07-04T12:00:00Z',
  },
]

/* ─── Workspace ─────────────────────────────────────────────────────────── */
export const DEMO_WORKSPACE = {
  id: WORKSPACE_ID,
  name: 'Pinnacle Micro Industries — BSE SME IPO',
  company_name: 'Pinnacle Micro Industries Limited',
  created_at: '2026-07-04T09:00:00Z',
}
