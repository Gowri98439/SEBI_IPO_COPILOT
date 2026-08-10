"""
Enterprise DRHP Pipeline Orchestrator — 12-Stage Async Pipeline

Replaces the monolithic build_drhp() function with a resumable, stage-isolated,
progress-reporting pipeline.

DESIGN RULES:
- Each stage has typed input/output
- Each stage writes its state to disk before returning (resumability)
- A crashed pipeline resumes from the last completed stage, not from stage 1
- Each stage error is isolated — other stages continue where possible
- Progress is reported via callback so callers can stream SSE events
- No blocking work on the main event loop — all heavy work via asyncio.to_thread()
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.schemas.drhp_v2 import (
    ConsistencyReport,
    DrhpPipelineState,
    DrhpRequestV2,
    FinancialIntelligenceReport,
    SectionOutput,
)

logger = logging.getLogger(__name__)

# Pipeline state persistence directory
_STATE_DIR = os.path.join(".", "pipeline_states")
os.makedirs(_STATE_DIR, exist_ok=True)

# ── In-memory job store (augmented by disk persistence) ─────────────────────
_jobs: Dict[str, Dict[str, Any]] = {}

# ── Stage names ─────────────────────────────────────────────────────────────
STAGES = [
    (1,  "Document Planner",               5),
    (2,  "Data Collector",                 10),
    (3,  "Financial Validator",            18),
    (4,  "RAG Retriever",                  25),
    (5,  "Section Generator",              70),   # Heaviest stage
    (6,  "Section Reviewer",               75),
    (7,  "Compliance Validator",           80),
    (8,  "Cross-Section Consistency",      85),
    (9,  "Chart & Table Generator",        90),
    (10, "Document Formatter",             93),
    (11, "PDF Generator",                  97),
    (12, "Intelligence Report Generator",  100),
]


# ── Persistence helpers ──────────────────────────────────────────────────────

def _state_path(job_id: str) -> str:
    return os.path.join(_STATE_DIR, f"{job_id}.json")


def _save_state(state: DrhpPipelineState) -> None:
    """Persist pipeline state to disk — enables resumability after crashes."""
    state.updated_at = datetime.now(timezone.utc).isoformat()
    try:
        with open(_state_path(state.job_id), "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not persist pipeline state for job %s: %s", state.job_id, exc)


def _load_state(job_id: str) -> Optional[DrhpPipelineState]:
    """Load persisted pipeline state from disk."""
    path = _state_path(job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DrhpPipelineState(**data)
    except Exception as exc:
        logger.warning("Could not load pipeline state for job %s: %s", job_id, exc)
        return None


def _save_sections(job_id: str, sections: Dict[str, SectionOutput]) -> None:
    """Persist generated sections to disk so they survive server restarts."""
    path = os.path.join(_STATE_DIR, f"{job_id}_sections.json")
    try:
        data = {sid: s.model_dump() for sid, s in sections.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as exc:
        logger.warning("Could not save sections for job %s: %s", job_id, exc)


def _load_sections(job_id: str) -> Dict[str, SectionOutput]:
    """Reload previously generated sections."""
    path = os.path.join(_STATE_DIR, f"{job_id}_sections.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {sid: SectionOutput(**v) for sid, v in data.items()}
    except Exception:
        return {}


# ── Pipeline result container ────────────────────────────────────────────────

class DrhpPipelineResult:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.sections: Dict[str, SectionOutput] = {}
        self.financial_report: Optional[FinancialIntelligenceReport] = None
        self.consistency_report: Optional[ConsistencyReport] = None
        self.compliance_results: List[Dict[str, Any]] = []
        self.charts: Dict[str, bytes] = {}
        self.drhp_pdf: Optional[bytes] = None
        self.intelligence_pdf: Optional[bytes] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stage_timings: Dict[str, float] = {}


# ── The Pipeline ──────────────────────────────────────────────────────────────

class DrhpPipeline:
    """
    12-stage async pipeline for enterprise DRHP generation.
    Produces two outputs: DRHP PDF + IPO Intelligence Report PDF.
    """

    def __init__(
        self,
        req: DrhpRequestV2,
        job_id: str,
        progress_cb: Optional[Callable[[int, str, str], None]] = None,
        resume: bool = True,
    ):
        self.req = req
        self.job_id = job_id
        self.progress_cb = progress_cb
        self.result = DrhpPipelineResult(job_id)
        self.resume = resume

        # Load or create state
        existing = _load_state(job_id) if resume else None
        if existing and existing.stage > 0:
            logger.info("Resuming pipeline job %s from stage %d", job_id, existing.stage)
            self.state = existing
            # Reload any already-generated sections
            self.result.sections = _load_sections(job_id)
        else:
            self.state = DrhpPipelineState(
                job_id=job_id,
                stage=0,
                status="planning",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            _save_state(self.state)

    def _report(self, pct: int, stage: str, message: str = "") -> None:
        """Update in-memory job store + call progress callback."""
        self.state.progress_pct = pct
        self.state.message = f"{stage}: {message}" if message else stage
        _jobs[self.job_id]["progress_pct"] = pct
        _jobs[self.job_id]["message"] = self.state.message
        _jobs[self.job_id]["current_stage"] = stage
        if self.progress_cb:
            try:
                self.progress_cb(pct, stage, message)
            except Exception:
                pass

    def _stage_start(self, stage_num: int, stage_name: str, pct: int) -> float:
        """Mark a stage as started."""
        self._report(pct, stage_name, "Starting...")
        logger.info("[Stage %d/%d] %s — starting", stage_num, len(STAGES), stage_name)
        return time.perf_counter()

    def _stage_done(self, stage_num: int, stage_name: str, t0: float) -> None:
        """Record stage completion time and update state."""
        elapsed = (time.perf_counter() - t0) * 1000
        self.result.stage_timings[stage_name] = elapsed
        self.state.stage = stage_num
        self.state.stage_timings[stage_name] = elapsed
        _save_state(self.state)
        logger.info("[Stage %d/%d] %s — done in %.0fms", stage_num, len(STAGES), stage_name, elapsed)

    # ── Stage 1: Document Planner ────────────────────────────────────────────
    async def _stage_document_planner(self) -> List[str]:
        """Decide which sections to generate based on company data completeness."""
        t0 = self._stage_start(1, "Document Planner", 3)
        from app.ai.section_generator import ALL_SECTION_IDS, SECTION_ROUTING

        target = self.req.target_sections or ALL_SECTION_IDS

        # If no financials, skip financial-statement-heavy sections
        if not self.req.financials:
            skip = {"financial_statements", "financial_ratios"}
            target = [s for s in target if s not in skip]
            self.result.warnings.append("Financial data not provided — financial ratio sections will show 'Missing Information'.")

        # If no ESG data, skip ESG section
        if not self.req.esg_metrics:
            self.result.warnings.append("ESG metrics not provided — ESG section will show 'Missing Information'.")

        logger.info("Document plan: %d sections selected", len(target))
        self._stage_done(1, "Document Planner", t0)
        return target

    # ── Stage 2: Data Collector ──────────────────────────────────────────────
    async def _stage_data_collector(self) -> Dict[str, Any]:
        """Collect and normalize all available data into a structured context."""
        t0 = self._stage_start(2, "Data Collector", 8)
        co = self.req.company
        context = {
            "company_name": co.name,
            "sector": co.sector,
            "financials_count": len(self.req.financials),
            "promoters_count": len(self.req.promoters),
            "has_legal_proceedings": bool(self.req.legal_proceedings),
            "has_esg": bool(self.req.esg_metrics),
            "has_credit_ratings": bool(self.req.credit_ratings),
            "has_peers": bool(self.req.peer_companies),
            "workspace_id": self.req.workspace_id,
        }
        self._stage_done(2, "Data Collector", t0)
        return context

    # ── Stage 3: Financial Validator ─────────────────────────────────────────
    async def _stage_financial_validator(self) -> FinancialIntelligenceReport:
        """Compute all financial ratios and run red-flag detection."""
        t0 = self._stage_start(3, "Financial Validator", 14)
        from app.ai.financial_intelligence import compute_financial_intelligence
        report = await asyncio.to_thread(compute_financial_intelligence, self.req)
        self.result.financial_report = report
        if report.red_flags:
            self.result.warnings.extend(report.red_flags)
        self._stage_done(3, "Financial Validator", t0)
        return report

    # ── Stage 4: RAG Retriever ───────────────────────────────────────────────
    async def _stage_rag_retriever(self, planned_sections: List[str]) -> Dict[str, str]:
        """
        Pre-fetch SEBI regulation context for all planned LLM sections.
        Returns dict of section_id → sebi_context string.
        """
        t0 = self._stage_start(4, "RAG Retriever", 22)
        from app.ai.section_generator import SECTION_ROUTING
        from app.ai.rag_pipeline import query_sebi_regulations

        section_contexts: Dict[str, str] = {}
        llm_sections = [
            sid for sid in planned_sections
            if SECTION_ROUTING.get(sid, ("", "algorithmic"))[1] in ("llm", "hybrid")
        ]

        for sid in llm_sections:
            title = SECTION_ROUTING[sid][0]
            try:
                docs = await query_sebi_regulations(
                    f"SEBI ICDR requirements for {title} section SME IPO",
                    top_k=3,
                )
                section_contexts[sid] = "\n\n".join(
                    f"[{d.get('regulation_id', 'SEBI')}] {d.get('content', '')[:400]}"
                    for d in docs
                )
            except Exception as exc:
                logger.warning("RAG retrieval failed for section %s: %s", sid, exc)
                section_contexts[sid] = ""

        self._stage_done(4, "RAG Retriever", t0)
        return section_contexts

    # ── Stage 5: Section Generator ───────────────────────────────────────────
    async def _stage_section_generator(
        self,
        planned_sections: List[str],
        fin_report: FinancialIntelligenceReport,
    ) -> Dict[str, SectionOutput]:
        """Generate all DRHP sections. Resumes from last checkpoint if restarting."""
        t0 = self._stage_start(5, "Section Generator", 28)
        from app.ai.section_generator import SectionGenerator

        generator = SectionGenerator(req=self.req, financial_report=fin_report)

        # Resume: skip sections already successfully generated
        already_done = set(self.result.sections.keys())
        remaining = [s for s in planned_sections if s not in already_done]
        total = len(planned_sections)
        done_count = len(already_done)

        if already_done:
            logger.info("Resuming section generation: %d/%d already complete", done_count, total)

        for i, section_id in enumerate(remaining):
            current_done = done_count + i
            pct = 28 + int((current_done / total) * 42)  # 28% → 70%
            title = self.req.company.name  # For progress message
            self._report(pct, "Section Generator", f"Generating: {section_id.replace('_', ' ').title()}")

            try:
                section = await generator.generate_section(section_id)
                self.result.sections[section_id] = section
                self.state.completed_sections.append(section_id)
            except Exception as exc:
                logger.error("Section generation failed for %s: %s", section_id, exc, exc_info=True)
                self.result.sections[section_id] = SectionOutput(
                    section_id=section_id,
                    title=section_id.replace("_", " ").title(),
                    content=f"[GENERATION ERROR: {exc}]\n[MISSING: All content for this section]",
                    missing_fields=[f"section_{section_id}"],
                    confidence=0.0,
                    generation_method="error",
                    review_status="rejected",
                )
                self.state.failed_sections.append(section_id)

            # Checkpoint after every 3 sections
            if (i + 1) % 3 == 0:
                _save_sections(self.job_id, self.result.sections)
                _save_state(self.state)

            await asyncio.sleep(0.05)  # Yield to event loop

        # Final save of all sections
        _save_sections(self.job_id, self.result.sections)
        self._stage_done(5, "Section Generator", t0)
        return self.result.sections

    # ── Stage 6: Section Reviewer ────────────────────────────────────────────
    async def _stage_section_reviewer(self, sections: Dict[str, SectionOutput]) -> Dict[str, SectionOutput]:
        """
        Review generated sections for quality and flag low-confidence outputs.
        In this version, reviewer applies rule-based quality checks.
        """
        t0 = self._stage_start(6, "Section Reviewer", 72)
        for section_id, section in sections.items():
            # Flag sections with very low confidence
            if section.confidence < 0.3:
                section.review_status = "rejected"
                self.result.warnings.append(
                    f"Section '{section.title}' has low confidence ({section.confidence:.2f}) — "
                    "human review required before filing."
                )
            elif section.missing_fields:
                section.review_status = "draft"
            else:
                section.review_status = "reviewed"

        self._stage_done(6, "Section Reviewer", t0)
        return sections

    # ── Stage 7: Compliance Validator ────────────────────────────────────────
    async def _stage_compliance_validator(self) -> List[Dict[str, Any]]:
        """Run SEBI compliance checks on key sections."""
        t0 = self._stage_start(7, "Compliance Validator", 77)
        results = []
        try:
            from app.ai.compliance_engine import run_compliance_checks
            # Compliance engine expects document text — build a summary context
            doc_text = f"""
Company: {self.req.company.name}
Sector: {self.req.company.sector}
Issue Size: Rs. {self.req.issue.issue_size_cr:.2f} Crore
Promoters: {len(self.req.promoters)} promoters
Financial Years: {len(self.req.financials)}
Objects: {self.req.issue.objects_of_issue[:300]}
"""
            # Lazy call — if compliance engine is unavailable, log and continue
            if callable(run_compliance_checks):
                results = await asyncio.to_thread(run_compliance_checks, doc_text)
        except ImportError:
            logger.warning("Compliance engine not available for pipeline integration — skipping.")
        except Exception as exc:
            logger.error("Compliance validation failed: %s", exc, exc_info=True)
            self.result.warnings.append(f"Compliance validation incomplete: {exc}")

        self.result.compliance_results = results
        self._stage_done(7, "Compliance Validator", t0)
        return results

    # ── Stage 8: Cross-Section Consistency ──────────────────────────────────
    async def _stage_consistency_check(self) -> ConsistencyReport:
        """Run 20-check consistency engine before generating PDF."""
        t0 = self._stage_start(8, "Cross-Section Consistency", 83)
        from app.ai.consistency_engine import run_consistency_checks
        report = await asyncio.to_thread(run_consistency_checks, self.req)
        self.result.consistency_report = report

        if report.errors:
            logger.warning("Consistency check found %d critical errors", len(report.errors))
            for err in report.errors:
                self.result.warnings.append(f"[CONSISTENCY ERROR] {err.check_name}: {err.description}")

        self._stage_done(8, "Cross-Section Consistency", t0)
        return report

    # ── Stage 9: Chart & Table Generator ─────────────────────────────────────
    async def _stage_chart_generator(self) -> Dict[str, bytes]:
        """Generate publication-quality charts from verified financial data."""
        t0 = self._stage_start(9, "Chart & Table Generator", 87)
        charts: Dict[str, bytes] = {}

        if not self.req.generate_charts or not self.req.financials:
            self._stage_done(9, "Chart & Table Generator", t0)
            return charts

        try:
            from app.services import drhp_charts as _charts
            fys = self.req.financials
            years = [fy.year for fy in fys]
            revenues = [fy.revenue for fy in fys]        # May contain None
            pats = [fy.net_profit for fy in fys]         # May contain None
            ebitdas = [fy.ebitda for fy in fys]          # May contain None — do NOT substitute 0

            # Chart 1: Revenue & PAT — only if at least one year has actual revenue data
            if any(r is not None and r > 0 for r in revenues):
                img = await asyncio.to_thread(_charts.revenue_pat_chart, years, revenues, pats)
                charts["revenue_pat"] = img

            # Chart 2: EBITDA trend — only if at least one year has actual EBITDA data
            if any(e is not None and e > 0 for e in ebitdas):
                img = await asyncio.to_thread(_charts.ebitda_trend_chart, years, ebitdas)
                charts["ebitda_trend"] = img

            # Chart 3: Shareholding pattern
            if self.req.promoters:
                promoter_pct = sum(p.holding_pct for p in self.req.promoters)
                public_pct = 100.0 - promoter_pct
                img = await asyncio.to_thread(
                    _charts.shareholding_chart,
                    ["Promoters & Promoter Group", "Public"],
                    [promoter_pct, public_pct],
                )
                charts["shareholding"] = img

            # Chart 4: Issue utilization (if structured)
            if self.req.issue.use_of_proceeds_structured:
                labels = [item.purpose for item in self.req.issue.use_of_proceeds_structured]
                amounts = [item.amount_lakhs for item in self.req.issue.use_of_proceeds_structured]
                img = await asyncio.to_thread(_charts.issue_utilization_chart, labels, amounts)
                charts["issue_utilization"] = img

        except Exception as exc:
            logger.error("Chart generation failed: %s", exc, exc_info=True)
            self.result.warnings.append(f"Chart generation failed: {exc}")

        self.result.charts = charts
        self._stage_done(9, "Chart & Table Generator", t0)
        return charts

    # ── Stage 10: Document Formatter ─────────────────────────────────────────
    async def _stage_document_formatter(
        self,
        sections: Dict[str, SectionOutput],
        consistency_report: ConsistencyReport,
    ) -> Dict[str, Any]:
        """Assemble the formatted document structure ready for PDF generation."""
        t0 = self._stage_start(10, "Document Formatter", 91)

        # Collect missing fields and compliance flags for appendix
        all_missing = []
        low_confidence = []
        for sid, section in sections.items():
            if section.missing_fields:
                all_missing.extend([(section.title, field) for field in section.missing_fields])
            if section.confidence < 0.5:
                low_confidence.append(section.title)

        formatted = {
            "sections": sections,
            "consistency_report": consistency_report,
            "all_missing_fields": all_missing,
            "low_confidence_sections": low_confidence,
            "generation_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "company": self.req.company.name,
                "total_sections": len(sections),
                "pipeline_version": "2.0",
            },
        }

        self._stage_done(10, "Document Formatter", t0)
        return formatted

    # ── Stage 11: PDF Generator ───────────────────────────────────────────────
    async def _stage_pdf_generator(
        self,
        sections: Dict[str, SectionOutput],
        formatted: Dict[str, Any],
        fin_report: FinancialIntelligenceReport,
    ) -> Optional[bytes]:
        """Generate the professional DRHP PDF using the upgraded drhp_service."""
        t0 = self._stage_start(11, "PDF Generator", 94)

        try:
            from app.services.drhp_service_v2 import build_enterprise_drhp_pdf
            pdf_bytes = await asyncio.to_thread(
                build_enterprise_drhp_pdf,
                self.req,
                sections,
                fin_report,
                self.result.charts,
                formatted.get("consistency_report"),
            )
            self.result.drhp_pdf = pdf_bytes
            _jobs[self.job_id]["pdf"] = pdf_bytes
            logger.info("DRHP PDF generated: %d bytes", len(pdf_bytes))
        except ImportError:
            # Fall back to existing drhp_service if v2 is not available
            try:
                from app.services.drhp_service import build_drhp, _jobs as _old_jobs
                from app.schemas.drhp import DrhpRequest, CompanyProfile, IssueDetails, FinancialYear
                # Build a v1 compatible request from v2 data
                v1_req = _build_v1_compat_request(self.req)
                pdf_bytes = await asyncio.to_thread(build_drhp, v1_req, self.job_id)
                self.result.drhp_pdf = pdf_bytes
                _jobs[self.job_id]["pdf"] = pdf_bytes
            except Exception as exc2:
                logger.error("PDF generation fallback also failed: %s", exc2, exc_info=True)
                self.result.errors.append(f"PDF generation failed: {exc2}")
                pdf_bytes = None
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc, exc_info=True)
            self.result.errors.append(f"PDF generation failed: {exc}")
            pdf_bytes = None

        self._stage_done(11, "PDF Generator", t0)
        return self.result.drhp_pdf

    # ── Stage 12: Intelligence Report ────────────────────────────────────────
    async def _stage_intelligence_report(
        self,
        fin_report: FinancialIntelligenceReport,
        consistency_report: ConsistencyReport,
        sections: Dict[str, SectionOutput],
    ) -> Optional[bytes]:
        """Generate the separate IPO Intelligence Report PDF."""
        t0 = self._stage_start(12, "Intelligence Report Generator", 97)

        if not self.req.generate_intelligence_report:
            self._stage_done(12, "Intelligence Report Generator", t0)
            return None

        try:
            from app.ai.intelligence_report import generate_intelligence_report
            report_bytes = await asyncio.to_thread(
                generate_intelligence_report,
                self.req,
                fin_report,
                consistency_report,
                sections,
                self.result.charts,
            )
            self.result.intelligence_pdf = report_bytes
            _jobs[self.job_id]["intelligence_pdf"] = report_bytes
            logger.info("Intelligence Report generated: %d bytes", len(report_bytes))
        except Exception as exc:
            logger.error("Intelligence report generation failed: %s", exc, exc_info=True)
            self.result.warnings.append(f"Intelligence Report generation failed: {exc}")

        self._stage_done(12, "Intelligence Report Generator", t0)
        return self.result.intelligence_pdf

    # ── Main run ──────────────────────────────────────────────────────────────
    async def run(self) -> DrhpPipelineResult:
        """Execute all 12 pipeline stages with resumability and error isolation."""
        pipeline_start = time.perf_counter()
        self.state.status = "running"
        _jobs[self.job_id]["status"] = "processing"
        _save_state(self.state)

        try:
            # Stage 1
            if self.state.stage < 1:
                planned_sections = await self._stage_document_planner()
            else:
                from app.ai.section_generator import ALL_SECTION_IDS
                planned_sections = self.req.target_sections or ALL_SECTION_IDS
                self._report(5, "Document Planner", "Resuming — skipped (already complete)")

            # Stage 2
            if self.state.stage < 2:
                context = await self._stage_data_collector()
            else:
                context = {}
                self._report(10, "Data Collector", "Resuming — skipped")

            # Stage 3
            if self.state.stage < 3:
                fin_report = await self._stage_financial_validator()
            else:
                fin_report = self.result.financial_report or FinancialIntelligenceReport()
                self._report(18, "Financial Validator", "Resuming — skipped")

            # Stage 4
            if self.state.stage < 4:
                _section_contexts = await self._stage_rag_retriever(planned_sections)
            else:
                _section_contexts = {}
                self._report(25, "RAG Retriever", "Resuming — skipped")

            # Stage 5 (always runs — skips completed sections internally)
            sections = await self._stage_section_generator(planned_sections, fin_report)

            # Stage 6
            if self.state.stage < 6:
                sections = await self._stage_section_reviewer(sections)
            else:
                self._report(75, "Section Reviewer", "Resuming — skipped")

            # Stage 7
            if self.state.stage < 7:
                compliance = await self._stage_compliance_validator()
            else:
                compliance = self.result.compliance_results
                self._report(80, "Compliance Validator", "Resuming — skipped")

            # Stage 8
            if self.state.stage < 8:
                consistency = await self._stage_consistency_check()
            else:
                consistency = self.result.consistency_report or ConsistencyReport(status="pass")
                self._report(85, "Cross-Section Consistency", "Resuming — skipped")

            # Stage 9
            if self.state.stage < 9:
                charts = await self._stage_chart_generator()
            else:
                charts = self.result.charts
                self._report(90, "Chart & Table Generator", "Resuming — skipped")

            # Stage 10
            if self.state.stage < 10:
                formatted = await self._stage_document_formatter(sections, consistency)
            else:
                formatted = {"sections": sections, "consistency_report": consistency}
                self._report(93, "Document Formatter", "Resuming — skipped")

            # Stage 11 (always run if PDF not yet present)
            if not self.result.drhp_pdf:
                await self._stage_pdf_generator(sections, formatted, fin_report)

            # Stage 12 (always run if intelligence not yet present)
            if not self.result.intelligence_pdf:
                await self._stage_intelligence_report(fin_report, consistency, sections)

            # ── Completion ────────────────────────────────────────────────
            total_elapsed = (time.perf_counter() - pipeline_start)
            self.state.status = "done"
            self.state.progress_pct = 100
            self.state.message = "Generation complete"
            _jobs[self.job_id]["status"] = "done"
            _jobs[self.job_id]["progress_pct"] = 100
            _jobs[self.job_id]["message"] = "Generation complete"
            _jobs[self.job_id]["drhp_ready"] = self.result.drhp_pdf is not None
            _jobs[self.job_id]["intelligence_report_ready"] = self.result.intelligence_pdf is not None
            _jobs[self.job_id]["total_time_seconds"] = total_elapsed
            _jobs[self.job_id]["sections_completed"] = len(sections)
            _jobs[self.job_id]["warnings"] = self.result.warnings[:20]   # Cap at 20 for API response
            _save_state(self.state)
            logger.info(
                "Pipeline job %s complete in %.1fs | %d sections | DRHP: %s | Intelligence: %s",
                self.job_id,
                total_elapsed,
                len(sections),
                "✓" if self.result.drhp_pdf else "✗",
                "✓" if self.result.intelligence_pdf else "✗",
            )

        except Exception as exc:
            logger.error("Pipeline job %s failed: %s", self.job_id, exc, exc_info=True)
            self.state.status = "error"
            self.state.errors.append(str(exc))
            _jobs[self.job_id]["status"] = "error"
            _jobs[self.job_id]["message"] = f"Pipeline error: {exc}"
            _save_state(self.state)
            self.result.errors.append(str(exc))

        return self.result


# ── V1 Compatibility Bridge ───────────────────────────────────────────────────

def _build_v1_compat_request(req: DrhpRequestV2):
    """Convert DrhpRequestV2 to DrhpRequest v1 for fallback PDF generation."""
    from app.schemas.drhp import DrhpRequest, CompanyProfile, PromoterDetail, FinancialYear, IssueDetails

    return DrhpRequest(
        company=CompanyProfile(
            name=req.company.name,
            cin=req.company.cin,
            pan=req.company.pan,
            incorporation_date=req.company.incorporation_date,
            registered_address=req.company.registered_address,
            sector=req.company.sector,
            sub_sector=req.company.sub_sector,
            website=req.company.website,
            description=req.company.description,
        ),
        promoters=[
            PromoterDetail(
                name=p.name,
                designation=p.designation,
                qualification=p.qualification,
                holding_pct=p.holding_pct,
            )
            for p in req.promoters
        ],
        financials=[
            FinancialYear(
                year=fy.year,
                revenue=fy.revenue,
                net_profit=fy.net_profit,
                total_assets=fy.total_assets,
                total_equity=fy.total_equity,
                ebitda=fy.ebitda or 0.0,
            )
            for fy in req.financials
        ],
        issue=IssueDetails(
            issue_size_cr=req.issue.issue_size_cr,
            fresh_issue_cr=req.issue.fresh_issue_cr,
            ofs_cr=req.issue.ofs_cr,
            price_band_low=req.issue.price_band_low,
            price_band_high=req.issue.price_band_high,
            face_value=req.issue.face_value,
            lot_size=req.issue.lot_size,
            objects_of_issue=req.issue.objects_of_issue,
            use_of_proceeds=req.issue.use_of_proceeds,
            merchant_banker=req.issue.merchant_banker,
        ),
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def start_pipeline(req: DrhpRequestV2, workspace_id: Optional[str] = None) -> str:
    """
    Start an async DRHP pipeline job. Returns job_id immediately.
    The pipeline runs in the background; poll /status/{job_id} for progress.
    """
    job_id = str(uuid.uuid4())
    req.workspace_id = workspace_id or req.workspace_id
    _jobs[job_id] = {
        "status": "pending",
        "progress_pct": 0,
        "message": "Queued",
        "current_stage": None,
        "pdf": None,
        "intelligence_pdf": None,
        "intelligence_report_ready": False,
        "warnings": [],
        "errors": [],
        "company_name": req.company.name,
    }

    async def _run_pipeline():
        pipeline = DrhpPipeline(req=req, job_id=job_id)
        await pipeline.run()

    asyncio.create_task(_run_pipeline())
    logger.info("Pipeline job %s created for company: %s", job_id, req.company.name)
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get current job state. Checks in-memory store, then disk."""
    job = _jobs.get(job_id)
    if job:
        return job
    # Try to reload from disk
    state = _load_state(job_id)
    if state:
        job = {
            "status": state.status,
            "progress_pct": state.progress_pct,
            "message": state.message,
            "warnings": state.errors,
            "company_name": getattr(state, "company_name", None),
        }
        _jobs[job_id] = job
        return job
    return None


def get_job_pdf(job_id: str) -> Optional[bytes]:
    return _jobs.get(job_id, {}).get("pdf")


def get_job_intelligence_pdf(job_id: str) -> Optional[bytes]:
    return _jobs.get(job_id, {}).get("intelligence_pdf")
