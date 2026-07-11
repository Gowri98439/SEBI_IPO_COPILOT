import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# ── Colors ──────────────────────────────────────────────────────────────────
PRIMARY = colors.HexColor("#003087")       # SEBI Navy
SECONDARY = colors.HexColor("#1A56DB")     # Slate Blue / Accent
TEXT_DARK = colors.HexColor("#0F172A")     # Charcoal
TEXT_BODY = colors.HexColor("#334155")     # Slate Text
TEXT_MUTED = colors.HexColor("#64748B")    # Muted Slate
BG_LIGHT = colors.HexColor("#F8FAFC")      # Elevated Light Grey
BG_HEADER = colors.HexColor("#EFF6FF")     # Soft Blue Header
BORDER_COLOR = colors.HexColor("#E2E8F0")  # Light Border
ACCENT_GOLD = colors.HexColor("#D97706")   # Amber
SUCCESS_COLOR = colors.HexColor("#059669") # Emerald

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page count and render professional
    running headers and footers across all pages except the cover page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        if self._pageNumber == 1:
            # Suppress header and footer on cover page
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(TEXT_MUTED)

        # Running Header
        self.drawString(54, 11 * inch - 36, "IPO COPILOT AI — A to Z PROJECT DOCUMENTATION")
        self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "SEBI TECHSPRINT 2026")
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.75)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.setFont("Helvetica", 8)
        self.drawString(54, 34, f"Generated: {datetime.now().strftime('%B %d, %Y')} | Confidential & Proprietary")
        self.drawRightString(8.5 * inch - 54, 34, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def create_a_to_z_pdf(filename="IPO_Copilot_AI_Project_Documentation_A_to_Z.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=PRIMARY,
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=14,
        leading=20,
        textColor=TEXT_MUTED,
        spaceAfter=24
    )
    h1_style = ParagraphStyle(
        "Header1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        "Header2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=SECONDARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h3_style = ParagraphStyle(
        "Header3",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=TEXT_DARK,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=TEXT_BODY,
        spaceAfter=8
    )
    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    code_style = ParagraphStyle(
        "CodeStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK,
        backColor=BG_LIGHT,
        borderColor=BORDER_COLOR,
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=8
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=TEXT_BODY
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=PRIMARY
    )

    story = []

    # ── COVER PAGE ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("IPO Copilot AI", title_style))
    story.append(Paragraph("AI-Driven Assistant for SME IPO Document Preparation & SEBI Compliance", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=3, color=PRIMARY, spaceAfter=24, spaceBefore=0))
    
    cover_meta = [
        [Paragraph("<b>Project Scope:</b>", table_header_style), Paragraph("SEBI Securities Market TechSprint Hackathon 2026", table_cell_style)],
        [Paragraph("<b>Core Focus:</b>", table_header_style), Paragraph("SME IPO DRHP Automation, ICDR 2018 Compliance, RAG Q&A Engine", table_cell_style)],
        [Paragraph("<b>Tech Stack:</b>", table_header_style), Paragraph("FastAPI 0.111, React 18, TypeScript, PostgreSQL 16, ChromaDB, LangChain, OpenAI / Groq", table_cell_style)],
        [Paragraph("<b>Document Version:</b>", table_header_style), Paragraph("v2.1.0 (Production Hardened & Verified)", table_cell_style)],
        [Paragraph("<b>Date of Issue:</b>", table_header_style), Paragraph(datetime.now().strftime("%B %d, %Y"), table_cell_style)]
    ]
    t_cover = Table(cover_meta, colWidths=[1.8 * inch, 5.2 * inch])
    t_cover.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, BORDER_COLOR),
        ('BOX', (0,0), (-1,-1), 1, PRIMARY)
    ]))
    story.append(t_cover)
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("<b>CONFIDENTIAL — PROPRIETARY SYSTEM DOCUMENTATION</b><br/>"
                           "This document contains comprehensive A-to-Z architectural, technical, operational, and algorithmic details of the IPO Copilot AI platform.", body_style))
    story.append(PageBreak())

    # ── 1. EXECUTIVE SUMMARY & VISION ───────────────────────────────────────
    story.append(Paragraph("1. Executive Summary & Vision", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "The preparation of a Draft Red Herring Prospectus (DRHP) for a Small and Medium Enterprise (SME) Initial Public Offering (IPO) is traditionally an arduous, highly manual process taking between 6 to 12 weeks. Merchant bankers, compliance officers, company secretaries, and SMEs must navigate hundreds of pages of complex SEBI Issue of Capital and Disclosure Requirements (ICDR) Regulations, Listing Obligations and Disclosure Requirements (LODR), and continuous SEBI circular updates.",
        body_style
    ))
    story.append(Paragraph(
        "<b>IPO Copilot AI</b> transforms this workflow by introducing an enterprise-grade, Retrieval-Augmented Generation (RAG) platform that reduces document preparation and regulatory compliance checking from weeks to days. Grounded strictly in SEBI regulations and specific workspace documents, the system eliminates AI hallucinations and provides full explainability for every recommendation.",
        body_style
    ))
    story.append(Paragraph("<b>Key Strategic Capabilities:</b>", h2_style))
    story.append(Paragraph("• <b>Automated DRHP & Document Intelligence:</b> Ingests financial statements, board resolutions, and background files using PyMuPDF and pdfplumber, chunking them into semantic sections with metadata preservation.", bullet_style))
    story.append(Paragraph("• <b>Real-Time ICDR Compliance Engine:</b> Runs automated rule-by-rule checks against SEBI ICDR 2018 regulations, classifying sections into Pass, Warning, or Fail with specific regulatory citations.", bullet_style))
    story.append(Paragraph("• <b>Evidence Rail & Explainable AI:</b> Every AI response provides exact traceability—displaying 'Why it matters', 'AI Reasoning', 'Confidence Scores', and direct text quotes from source documents.", bullet_style))
    story.append(Paragraph("• <b>Persistent & Floating SEBI Advisor (Copilot):</b> A multi-turn conversational AI widget that streams answers via Server-Sent Events (SSE), persists history across sessions, and prioritizes workspace files over general SEBI corpus.", bullet_style))
    story.append(Paragraph("• <b>Draft Review & Section Generator:</b> Performs section-level gap analysis, highlights omissions, and generates formal legal drafts for mandatory DRHP sections (e.g., Risk Factors, Objects of Issue, Basis for Issue Price).", bullet_style))

    # ── 2. SYSTEM ARCHITECTURE & TOPOLOGY ───────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(Paragraph("2. System Architecture & Topology", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "IPO Copilot AI employs a clean, modular, multi-tier architecture designed for horizontal scalability, strict tenant isolation, and fault tolerance. The platform separates presentation, asynchronous REST API orchestration, vector retrieval, and relational storage.",
        body_style
    ))

    arch_diagram = """
┌───────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                 │
│          React 18 + Vite + TypeScript + TailwindCSS + Zustand             │
│   [Dashboard]  [Document Upload]  [Compliance Check]  [Floating Copilot]  │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │ REST APIs / SSE Streaming (Port 8000)
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                          API & ORCHESTRATION LAYER                        │
│                FastAPI 0.111 · Python 3.11 · Async Uvicorn                │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│ │ Auth & JWT   │ │ Workspace &  │ │ Compliance & │ │ RAG & Copilot      │ │
│ │ Middleware   │ │ Document CRUD│ │ Review Engine│ │ Router (SSE stream)│ │
│ └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘ │
└──────────┬──────────────────────────┬───────────────────────────┬─────────┘
           │ Asyncpg / SQLAlchemy     │ Chroma SDK                │ HTTPS
┌──────────▼──────────┐    ┌──────────▼──────────┐     ┌──────────▼─────────┐
│  PostgreSQL 16 (DB) │    │ ChromaDB (VectorDB) │     │ OpenAI / Groq LLMs │
│ • Users, Workspaces │    │ • SEBI 2026 Corpus  │     │ • gpt-4o-mini      │
│ • Documents, Chunks │    │ • Uploaded DRHP Chunks│   │ • all-MiniLM-L6-v2 │
│ • Compliance & Logs │    │ • MMR Hybrid Search │     │ • text-embedding-3 │
└─────────────────────┘    └─────────────────────┘     └────────────────────┘
"""
    story.append(Paragraph(arch_diagram.strip().replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    # ── 3. TECHNOLOGY STACK & DEPENDENCIES ──────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(Paragraph("3. Technology Stack & Dependencies", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    
    stack_data = [
        [Paragraph("<b>Layer</b>", table_header_style), Paragraph("<b>Technology & Version</b>", table_header_style), Paragraph("<b>Core Purpose & Design Rationale</b>", table_header_style)],
        [Paragraph("<b>Backend Runtime</b>", table_cell_style), Paragraph("Python 3.11 + FastAPI 0.111", table_cell_style), Paragraph("Provides high-throughput async API endpoints, strict Pydantic v2 validation, and automatic OpenAPI documentation.", table_cell_style)],
        [Paragraph("<b>ORM & Database</b>", table_cell_style), Paragraph("SQLAlchemy 2.0 + Asyncpg<br/>PostgreSQL 16 / SQLite", table_cell_style), Paragraph("Async connection pooling, clean relational schema for multi-tenant workspace isolation, and Alembic migrations.", table_cell_style)],
        [Paragraph("<b>Vector Store</b>", table_cell_style), Paragraph("ChromaDB 0.5 (Persistent)", table_cell_style), Paragraph("Stores high-dimensional vector embeddings for SEBI ICDR regulations, circulars, and uploaded company files.", table_cell_style)],
        [Paragraph("<b>AI & RAG Engine</b>", table_cell_style), Paragraph("LangChain 0.2 + OpenAI / Groq<br/>Sentence-Transformers", table_cell_style), Paragraph("Orchestrates semantic retrieval, MMR hybrid ranking, prompt formatting, and LLM streaming (GPT-4o-mini / Llama-3). Uses local `all-MiniLM-L6-v2` for offline-resilient embeddings.", table_cell_style)],
        [Paragraph("<b>Document Parsing</b>", table_cell_style), Paragraph("PyMuPDF (fitz) + pdfplumber", table_cell_style), Paragraph("Extracts raw text, page numbers, tables, and document metadata from uploaded DRHP PDFs and financial reports.", table_cell_style)],
        [Paragraph("<b>Frontend Core</b>", table_cell_style), Paragraph("React 18 + Vite 5 + TypeScript", table_cell_style), Paragraph("Ultra-fast client-side rendering, strict typing across all API contracts, and hot module replacement.", table_cell_style)],
        [Paragraph("<b>State & UI</b>", table_cell_style), Paragraph("TanStack Query v5 + Zustand<br/>TailwindCSS + Lucide Icons", table_cell_style), Paragraph("Global server-state caching (5min stale time), reactive client state, and modern SEBI Navy design system.", table_cell_style)]
    ]
    t_stack = Table(stack_data, colWidths=[1.5 * inch, 2.2 * inch, 3.3 * inch])
    t_stack.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_HEADER),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_stack)

    # ── 4. END-TO-END WORKFLOW & USER JOURNEY ───────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("4. End-to-End Workflow & User Journey", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "The platform guides merchant bankers and compliance officers through a structured, 7-stage lifecycle to transform raw source documents into verified, SEBI-compliant IPO filings:",
        body_style
    ))
    
    stages = [
        ("Stage 1: Authentication & Workspace Tenancy", "Users register and authenticate via secure JWT (`/api/v1/auth/login`). Upon login, the user selects or creates a dedicated Workspace (e.g., 'Acme Robotics SME IPO'). Every subsequent operation is strictly scoped to this `workspace_id` to prevent cross-company data leakage."),
        ("Stage 2: Document Ingestion & Chunking", "Users upload source PDFs (DRHP drafts, audited financials, board resolutions) via `/api/v1/workspaces/{id}/documents`. The backend saves files to `UPLOAD_DIR`, extracts text via PyMuPDF, divides content into 1000-character semantic chunks (with 150-char overlap), and indexes them into both PostgreSQL (`document_chunks`) and ChromaDB vector store (`get_workspace_vectorstore`)."),
        ("Stage 3: Automated SEBI Compliance Checking", "Triggered via `/api/v1/workspaces/{id}/compliance/check`. The engine loads the SEBI SME Checklist (`sebi_rules.json`), retrieves relevant document chunks via vector similarity, and prompts the LLM to verify compliance. Each check outputs: Status (`pass`, `warning`, `fail`), Exact Quote Evidence, Regulatory Reference, and Confidence Score."),
        ("Stage 4: Draft Review & Gap Analysis", "Users submit specific DRHP sections (e.g., 'Risk Factors') for deep review via `/api/v1/workspaces/{id}/reviews`. The AI compares the text against mandatory SEBI disclosures, highlighting missing sub-clauses, vague risk phrasing, and providing drop-in replacement suggestions."),
        ("Stage 5: Professional DRHP Chart & Visual Analytics Generation", "In the DRHP Generator (`/api/v1/workspaces/{id}/drhp/generate`), the backend computes and attaches 3 professional visual analytics modules via `drhp_charts.py`: (1) Peer Comparison Bar Charts (P/E, RoNW, EBITDA vs listed peers), (2) Funds Utilization Donut Charts (Objects of Issue breakdown), and (3) Revenue & PAT CAGR Trajectory Line Charts."),
        ("Stage 6: Persistent Copilot Chat & Evidence Rail", "Users interact with the floating `FloatingCopilot` widget across any page or navigate to the full SEBI Advisor page. When a query is asked, the `rag_query_full` pipeline searches workspace documents first, supplements with SEBI regulations, and streams tokens via Server-Sent Events (`SSE`). The Evidence Rail displays full explainability citations."),
        ("Stage 7: Audit Log Traceability & Export", "All user actions (document uploads, compliance runs, AI prompts, status updates) are cryptographically hashed and logged to `audit_events`. Users export final validation reports and audit logs as downloadable PDFs or Excel summaries via `/api/v1/workspaces/{id}/export`.")
    ]
    for title, desc in stages:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))

    # ── 5. CORE AI & RAG PIPELINE SPECIFICATIONS ────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("5. Core AI & RAG Pipeline Specifications", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "At the heart of IPO Copilot AI is an advanced, multi-stage Retrieval-Augmented Generation (RAG) architecture tailored specifically for Indian capital markets and SEBI regulatory precision.",
        body_style
    ))
    
    story.append(Paragraph("<b>5.1 Multi-Tier RAG Routing (`rag_pipeline.py`)</b>", h2_style))
    story.append(Paragraph(
        "To ensure high precision and eliminate generic advice, the `rag_query_full()` engine implements a strict 2-tier retrieval prioritization:",
        body_style
    ))
    story.append(Paragraph("1. <b>Workspace Vector Store Priority:</b> The system first queries the workspace-specific ChromaDB collection (`get_workspace_vectorstore(workspace_id)`) using `top_k=5`. If specific company documents (e.g., uploaded DRHP or balance sheets) contain relevant chunks, they are immediately placed at the top of the context prompt.", bullet_style))
    story.append(Paragraph("2. <b>SEBI Corpus Supplementation:</b> The system then queries the global SEBI regulatory vector store (`get_sebi_vectorstore()`). If workspace documents were already found, SEBI retrieval is dynamically tuned to `top_k=1` (purely for regulatory backing). If no workspace documents match, SEBI retrieval expands to `top_k=5` using Maximal Marginal Relevance (`MMR`, `fetch_k=15`) to ensure diverse clause coverage.", bullet_style))

    story.append(Paragraph("<b>5.2 SEBI 2026 Corpus & Amendments Integration (`sebi_corpus/`)</b>", h2_style))
    story.append(Paragraph(
        "The AI engine is pre-indexed with a rich, curated repository of capital markets regulations, verified up to Q1-Q2 2026 (`v2.1.0`):",
        body_style
    ))
    
    corpus_items = [
        [Paragraph("<b>Corpus File</b>", table_header_style), Paragraph("<b>Size</b>", table_header_style), Paragraph("<b>Regulatory Coverage & Content Scope</b>", table_header_style)],
        [Paragraph("`icdr_regulations.txt`", table_cell_style), Paragraph("28.0 KB", table_cell_style), Paragraph("SEBI (Issue of Capital and Disclosure Requirements) Regulations, 2018 — Chapter IX SME IPO eligibility, lock-in rules, promoter contribution, and pricing mandates.", table_cell_style)],
        [Paragraph("`lodr_regulations.txt`", table_cell_style), Paragraph("19.7 KB", table_cell_style), Paragraph("SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 — Corporate governance, audit committee composition, and mandatory disclosures.", table_cell_style)],
        [Paragraph("`sebi_2026_amendments.txt`", table_cell_style), Paragraph("17.7 KB", table_cell_style), Paragraph("Latest 2026 SEBI Circulars: Digital DRHP filings via PRISM portal, mandatory AI-generated content disclosure, UPI-only ASBA limits, Green IPO sustainability frameworks, and GIFT City dual-listing norms.", table_cell_style)],
        [Paragraph("`sme_ipo_guidelines.txt`", table_cell_style), Paragraph("18.5 KB", table_cell_style), Paragraph("NSE Emerge and BSE SME specific listing criteria, post-issue capital thresholds (min Rs. 1 crore, max Rs. 25 crore), and market making requirements.", table_cell_style)],
        [Paragraph("`drhp_*_factors.txt`", table_cell_style), Paragraph("42.2 KB", table_cell_style), Paragraph("Standardized templates and risk factor taxonomies for Business Overview, Risk Factors, and Financial Statements drafting.", table_cell_style)]
    ]
    t_corpus = Table(corpus_items, colWidths=[1.8 * inch, 0.8 * inch, 4.4 * inch])
    t_corpus.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_HEADER),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_corpus)

    story.append(Paragraph("<b>5.3 Anti-Hallucination & Explainability Guardrails</b>", h2_style))
    story.append(Paragraph(
        "In high-stakes financial compliance, hallucinated advice can lead to regulatory rejection or severe penalties. IPO Copilot AI enforces strict architectural guardrails:",
        body_style
    ))
    story.append(Paragraph("• <b>System Guard & Prompt Sanitization (`SYSTEM_GUARD`):</b> All user inputs and system instructions are wrapped in strict formatting instructions. If retrieved context docs (`context_docs`) are empty, the prompt explicitly instructs the LLM: <i>'If the context does not contain the answer, you MUST return EXACTLY: No supporting evidence found. Do not hallucinate or guess.'</i>", bullet_style))
    story.append(Paragraph("• <b>Evidence Rail UI (`EvidenceRail.tsx`):</b> Every compliance check or chat answer parses the LLM output into distinct visual compartments: <b>Why it matters</b> (regulatory impact), <b>AI Reasoning</b> (deductive logic applied), and <b>Supporting Citations</b> (exact verbatim text quotes from page X of document Y).", bullet_style))
    story.append(Paragraph("• <b>Offline-Resilient Embedding Router (`model_router.py`):</b> To prevent cloud embedding API rate limits or 404 region errors (`text-embedding-004`), the system hardcodes/prefers local `sentence-transformers/all-MiniLM-L6-v2` (`local_minilm`) for blazing-fast vector embeddings directly inside the backend container.", bullet_style))

    # ── 6. DATABASE & DATA MODEL ARCHITECTURE ───────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("6. Database & Data Model Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "The relational database layer is managed by async SQLAlchemy (`database.py`) and structured around strict foreign-key relationships ensuring full workspace isolation.",
        body_style
    ))
    
    db_models = [
        [Paragraph("<b>Model / Table</b>", table_header_style), Paragraph("<b>Key Attributes & Foreign Keys</b>", table_header_style), Paragraph("<b>Description & Lifecycle Role</b>", table_header_style)],
        [Paragraph("`User` (`users`)", table_cell_style), Paragraph("`id` (PK), `email`, `hashed_password`, `full_name`, `role`, `is_active`", table_cell_style), Paragraph("Stores authenticated merchant bankers and SME users. Linked to RefreshTokens and Workspaces.", table_cell_style)],
        [Paragraph("`Workspace` (`workspaces`)", table_cell_style), Paragraph("`id` (PK), `name`, `description`, `user_id` (FK -> users.id), `created_at`", table_cell_style), Paragraph("The core multi-tenant boundary. Every document, compliance check, review, and chat thread belongs to one workspace.", table_cell_style)],
        [Paragraph("`Company` (`companies`)", table_cell_style), Paragraph("`id` (PK), `workspace_id` (FK), `name`, `cin`, `sector`, `incorporation_date`, `paid_up_capital`", table_cell_style), Paragraph("Contains corporate profile and capital metrics used to auto-evaluate SME eligibility thresholds.", table_cell_style)],
        [Paragraph("`Document` (`documents`)", table_cell_style), Paragraph("`id` (PK), `workspace_id` (FK), `filename`, `file_path`, `file_size`, `doc_type`, `version`, `status`", table_cell_style), Paragraph("Tracks uploaded files (`drhp_draft`, `financials`, `board_resolution`) with automated version incrementing.", table_cell_style)],
        [Paragraph("`DocumentChunk` (`document_chunks`)", table_cell_style), Paragraph("`id` (PK), `document_id` (FK), `chunk_index`, `content`, `page_number`, `chroma_id`", table_cell_style), Paragraph("Stores semantic text segments in PostgreSQL alongside exact mapping IDs to ChromaDB vectors.", table_cell_style)],
        [Paragraph("`ComplianceCheck` (`compliance_checks`)", table_cell_style), Paragraph("`id` (PK), `workspace_id` (FK), `rule_id`, `rule_name`, `status`, `evidence`, `why`, `confidence`", table_cell_style), Paragraph("Records the structured JSON output of automated SEBI ICDR evaluations for the workspace.", table_cell_style)],
        [Paragraph("`CopilotThread` & `CopilotMessage`", table_cell_style), Paragraph("`id` (PK), `workspace_id` (FK), `thread_id` (FK), `role` (`user`/`assistant`), `content`, `rag_sources`", table_cell_style), Paragraph("Persists all multi-turn conversational histories, allowing users to resume advisory chats anytime.", table_cell_style)],
        [Paragraph("`Review` (`reviews`)", table_cell_style), Paragraph("`id` (PK), `workspace_id` (FK), `document_id` (FK), `section_name`, `status`, `comments_json`", table_cell_style), Paragraph("Stores section-level draft reviews, actionable AI suggestions, and human sign-off statuses.", table_cell_style)],
        [Paragraph("`AuditEvent` (`audit_events`)", table_cell_style), Paragraph("`id` (PK), `workspace_id` (FK), `user_id` (FK), `action`, `resource_type`, `details`, `ip_address`", table_cell_style), Paragraph("Immutable trail of all regulatory actions, logins, and document modifications for compliance audits.", table_cell_style)]
    ]
    t_db = Table(db_models, colWidths=[1.5 * inch, 2.3 * inch, 3.2 * inch])
    t_db.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_HEADER),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_db)

    # ── 7. SECURITY & PRODUCTION HARDENING ──────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("7. Security & Production Hardening", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "As an enterprise capital markets application, IPO Copilot AI has undergone rigorous security stabilization and hardening across all endpoints:",
        body_style
    ))
    story.append(Paragraph("<b>7.1 Strict Workspace Tenancy Isolation</b>", h2_style))
    story.append(Paragraph(
        "To prevent horizontal privilege escalation or data cross-talk, every API router (`documents.py`, `compliance.py`, `copilot.py`, `reviews.py`, `drhp.py`) enforces explicit workspace ownership validation using the authenticated JWT `current_user`:",
        body_style
    ))
    story.append(Paragraph("`workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == current_user.id))`", code_style))
    story.append(Paragraph("If the query returns `None`, the API immediately raises an HTTP `404 Not Found` or `403 Forbidden`, ensuring users can never enumerate or access documents belonging to other SMEs.", body_style))

    story.append(Paragraph("<b>7.2 Path Traversal & File System Protections</b>", h2_style))
    story.append(Paragraph(
        "File upload (`/workspaces/{id}/documents/upload`) and download endpoints strictly sanitize incoming filenames and verify absolute directory boundaries before performing disk I/O:",
        body_style
    ))
    story.append(Paragraph("• Filenames are stripped of path components using `os.path.basename(file.filename)` and validated against allowed extensions (`.pdf`, `.docx`, `.txt`, `.xlsx`).", bullet_style))
    story.append(Paragraph("• Target paths are resolved using `Path(upload_path).resolve()` and asserted to start with `Path(settings.UPLOAD_DIR).resolve()`, preventing directory traversal (`../../etc/passwd`) attacks.", bullet_style))

    story.append(Paragraph("<b>7.3 API Rate Limiting & Global Exception Handling</b>", h2_style))
    story.append(Paragraph("• <b>Rate Limiting (`slowapi`):</b> High-cost AI generation and authentication endpoints are throttled. For example, `POST /workspaces/{id}/copilot/chat` is protected by `@limiter.limit('30/minute')`, preventing Denial-of-Service or OpenAI/Groq API budget exhaustion.", bullet_style))
    story.append(Paragraph("• <b>Global Exception Handlers (`main.py`):</b> Custom async exception handlers intercept `SQLAlchemyError`, `asyncio.TimeoutError`, and unhandled `Exception` instances. Instead of exposing internal stack traces or SQL schemas to clients, the API returns standardized, clean JSON responses: `{'success': False, 'error': {'code': 'DATABASE_ERROR', 'message': '...'}}`.", bullet_style))

    # ── 8. FRONTEND ARCHITECTURE & DESIGN SYSTEM ────────────────────────────
    story.append(Spacer(1, 10))
    story.append(Paragraph("8. Frontend Architecture & Design System", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "The client application (`frontend/`) is built with React 18, Vite, TypeScript, and a custom SEBI Navy enterprise design system (`index.css`) emphasizing visual clarity, density, and responsiveness.",
        body_style
    ))
    story.append(Paragraph("<b>8.1 State Management Architecture</b>", h2_style))
    story.append(Paragraph("• <b>TanStack Query v5 (Server State):</b> All asynchronous backend queries (`useWorkspaces`, `useDocuments`, `useComplianceChecks`) use TanStack Query with a global `staleTime: 5 * 60 * 1000` (5 minutes) and `gcTime: 30 * 60 * 1000` (30 minutes). This eliminates unnecessary API polling, caches RAG results, and guarantees instant tab switching.", bullet_style))
    story.append(Paragraph("• <b>Zustand Stores (Client State):</b> `useAuthStore` manages JWT tokens (`access_token`) and current user profiles. `useWorkspaceStore` tracks the active `currentWorkspaceId` and `currentWorkspaceName` across all route transitions.", bullet_style))
    story.append(Paragraph("• <b>Chat Context (`ChatContext.tsx`):</b> Manages multi-thread conversational state, persisting local chat backups to `localStorage` while synchronizing with the backend `CopilotThread` tables.", bullet_style))

    story.append(Paragraph("<b>8.2 Key Interactive UI Components</b>", h2_style))
    story.append(Paragraph("• <b>`FloatingCopilot.tsx` (Persistent ChatGPT Widget):</b> Mounted globally inside `AppShell.tsx`, this floating blue widget stays visible across all pages without unmounting during route navigation. Users can expand/collapse the panel, switch chat threads from the mini sidebar, and stream responses with real-time typing indicators (`● Thinking…`).", bullet_style))
    story.append(Paragraph("• <b>`ReadinessGauge.tsx` (SME IPO Readiness Score):</b> Renders an interactive Recharts radial gauge on the dashboard, computing a composite 0-100 score based on uploaded documents and compliance check pass rates, categorized into 'Ready to File' (`>=80`), 'In Progress' (`>=60`), or 'Needs Attention'.", bullet_style))
    story.append(Paragraph("• <b>`EvidenceRail.tsx` & `ComplianceCheckRow.tsx`:</b> Collapsible cards displaying compliance statuses (`Pass ▲`, `Review ■`, `Critical ▲`), exact regulatory quotes, and direct page-link citations.", bullet_style))

    # ── 9. DEPLOYMENT & OPERATIONS GUIDE ────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("9. Deployment & Operations Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "IPO Copilot AI is container-native and orchestrated via Docker Compose (`docker-compose.yml`), enabling one-click deployment across developer workstations or cloud instances.",
        body_style
    ))
    story.append(Paragraph("<b>9.1 Container Services Overview</b>", h2_style))
    story.append(Paragraph("1. `postgres` (`postgres:16-alpine`): Exposes port `5432` with health checks (`pg_isready -U ipo -d ipo_copilot`) and persistent volume `postgres_data`.", bullet_style))
    story.append(Paragraph("2. `backend` (`FastAPI / Python 3.11`): Exposes port `8000`, waits for `postgres:service_healthy`, mounts `backend_uploads` (`/app/uploads`) and `backend_chroma` (`/app/chroma_db`), and executes `uvicorn app.main:app`.", bullet_style))
    story.append(Paragraph("3. `frontend` (`node:20-alpine`): Exposes port `3000`, runs Vite dev/build server (`npm run dev -- --host 0.0.0.0`), connecting to the backend via CORS.", bullet_style))

    story.append(Paragraph("<b>9.2 Essential Environment Variables (`.env`)</b>", h2_style))
    env_data = [
        [Paragraph("<b>Variable</b>", table_header_style), Paragraph("<b>Default / Example Value</b>", table_header_style), Paragraph("<b>Operational Purpose</b>", table_header_style)],
        [Paragraph("`DATABASE_URL`", table_cell_style), Paragraph("`postgresql+asyncpg://ipo:ipo123@postgres:5432/ipo_copilot`", table_cell_style), Paragraph("Async SQLAlchemy database connection string.", table_cell_style)],
        [Paragraph("`SECRET_KEY`", table_cell_style), Paragraph("`hackathon-secret-key-change-in-prod`", table_cell_style), Paragraph("Cryptographic signing secret for JWT authentication tokens.", table_cell_style)],
        [Paragraph("`OPENAI_API_KEY`", table_cell_style), Paragraph("`sk-proj-...` or `gsk_...` (Groq)", table_cell_style), Paragraph("API key for LLM generation (`LLM_MODEL=gpt-4o-mini`).", table_cell_style)],
        [Paragraph("`EMBEDDING_MODEL`", table_cell_style), Paragraph("`all-MiniLM-L6-v2`", table_cell_style), Paragraph("Specifies the HuggingFace local embedding model used by `model_router.py`.", table_cell_style)],
        [Paragraph("`CHROMA_PERSIST_DIR`", table_cell_style), Paragraph("`/app/chroma_db`", table_cell_style), Paragraph("Absolute path to persistent vector database directory.", table_cell_style)]
    ]
    t_env = Table(env_data, colWidths=[1.8 * inch, 2.2 * inch, 3.0 * inch])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_HEADER),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_env)

    story.append(Paragraph("<b>9.3 Automated Verification Scripts (`verify_e2e.py`)</b>", h2_style))
    story.append(Paragraph(
        "The repository includes comprehensive verification suites (`verify_e2e.py`, `verify_outputs.py`, `test_api.py`) that programmatically assert API health, user registration, token generation, workspace isolation, document upload processing, and compliance check execution.",
        body_style
    ))

    # ── 10. KNOWN LIMITATIONS & ROADMAP ─────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(Paragraph("10. Known Limitations & Production Roadmap", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY, spaceAfter=12, spaceBefore=0))
    story.append(Paragraph(
        "While IPO Copilot AI is stable, audited, and production-hardened, several scalability enhancements are outlined for Phase 2 commercial rollout (`KNOWN_LIMITATIONS.md`):",
        body_style
    ))
    story.append(Paragraph("1. <b>Object Storage Migration (AWS S3 / Azure Blob):</b> Currently, uploaded files reside on the local disk (`UPLOAD_DIR`). For multi-node Kubernetes clusters, file storage must migrate to S3 to ensure load-balanced instances can access uploaded PDFs uniformly.", bullet_style))
    story.append(Paragraph("2. <b>Distributed Vector Store Scaling:</b> While local persistent ChromaDB performs exceptionally well for SME IPO corpora (`~100,000` chunks), enterprise SaaS deployments handling thousands of concurrent merchant bankers should scale to distributed vector stores such as Pinecone, Qdrant, or Milvus.", bullet_style))
    story.append(Paragraph("3. <b>Specialized OCR for Dense Financial Tables:</b> Standard PDF extraction (`fitz`/`pdfplumber`) extracts text reliably but may flatten highly complex, multi-page audited financial tables. Integrating tabular OCR (e.g., Amazon Textract or specialized LLM vision parsers) will further elevate numerical precision during balance sheet cross-checking.", bullet_style))
    story.append(Paragraph("4. <b>WebSocket Fallback for SSE:</b> Server-Sent Events (`SSE`) power our streaming chat effectively. However, certain strict corporate banking firewalls occasionally drop idle HTTP streams; implementing a dual SSE/WebSocket adapter will maximize connection resilience.", bullet_style))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated comprehensive A-to-Z project documentation: {filename}")

if __name__ == "__main__":
    create_a_to_z_pdf()
