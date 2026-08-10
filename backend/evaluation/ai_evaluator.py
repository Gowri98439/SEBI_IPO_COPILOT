"""
AI Quality Evaluation Framework for IPO Copilot AI.
Measures retrieval precision/recall, hallucination detection, and DRHP completeness.

Run: pytest backend/evaluation/ -v
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Evaluation Dataset ─────────────────────────────────────────────────────
# Ground truth questions with expected regulation references and answer constraints.
SEBI_EVALUATION_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question": "What is the minimum net worth required for an SME IPO on NSE Emerge?",
        "expected_regulation": "SEBI ICDR",
        "expected_keywords": ["crore", "net worth", "SME", "emerge"],
        "unsupported_claims": ["10 crore", "50 crore"],  # can't claim a specific figure without evidence
        "category": "eligibility",
    },
    {
        "question": "What disclosures are required for promoter shareholding in an SME DRHP?",
        "expected_regulation": "SEBI ICDR",
        "expected_keywords": ["promoter", "shareholding", "lock-in", "disclosure"],
        "unsupported_claims": ["no lock-in required", "lock-in not applicable"],
        "category": "disclosure",
    },
    {
        "question": "What financial statements must accompany an SME IPO DRHP?",
        "expected_regulation": "SEBI ICDR",
        "expected_keywords": ["audited", "financial", "statement", "years"],
        "unsupported_claims": [],
        "category": "financial",
    },
    {
        "question": "What are the risk factor disclosure requirements for a DRHP?",
        "expected_regulation": "SEBI ICDR",
        "expected_keywords": ["risk", "factor", "material", "investor"],
        "unsupported_claims": ["no material risks", "risk-free investment"],
        "category": "risk",
    },
    {
        "question": "What is the minimum lot size for SME IPO on BSE SME?",
        "expected_regulation": "SEBI ICDR",
        "expected_keywords": ["lot size", "minimum", "applicant", "BSE SME"],
        "unsupported_claims": [],
        "category": "issue_structure",
    },
]


# ── Metric dataclasses ──────────────────────────────────────────────────────

@dataclass
class RetrievalMetrics:
    precision: float = 0.0         # Retrieved relevant / total retrieved
    recall: float = 0.0            # Retrieved relevant / total relevant
    mrr: float = 0.0               # Mean Reciprocal Rank
    keyword_hit_rate: float = 0.0  # Fraction of expected keywords found in retrieved chunks


@dataclass
class HallucinationMetrics:
    total_checked: int = 0
    unsupported_claims_found: int = 0
    hallucination_rate: float = 0.0   # unsupported / total_checked
    injection_attempts_detected: int = 0


@dataclass
class DRHPCompletenessMetrics:
    total_sections: int = 0
    sections_with_content: int = 0
    sections_with_missing_info: int = 0
    sections_with_evidence: int = 0
    completeness_pct: float = 0.0


@dataclass
class AIEvaluationReport:
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    hallucination: HallucinationMetrics = field(default_factory=HallucinationMetrics)
    completeness: DRHPCompletenessMetrics = field(default_factory=DRHPCompletenessMetrics)
    overall_score: float = 0.0
    notes: List[str] = field(default_factory=list)


# ── Evaluation functions ────────────────────────────────────────────────────

def evaluate_retrieval_quality(
    question: str,
    retrieved_chunks: List[str],
    expected_keywords: List[str],
    relevant_chunk_count: Optional[int] = None,
) -> RetrievalMetrics:
    """
    Evaluate retrieval quality for a given question.
    
    Args:
        question: The question asked.
        retrieved_chunks: Text chunks returned by the RAG pipeline.
        expected_keywords: Words/phrases expected in relevant chunks.
        relevant_chunk_count: If known, how many relevant chunks exist in corpus.
    """
    if not retrieved_chunks:
        return RetrievalMetrics()

    # Keyword hit rate: what fraction of expected keywords appear in ANY retrieved chunk?
    combined_text = " ".join(retrieved_chunks).lower()
    keywords_found = sum(1 for kw in expected_keywords if kw.lower() in combined_text)
    keyword_hit_rate = keywords_found / len(expected_keywords) if expected_keywords else 0.0

    # Relevant chunk count (simplified: chunk is "relevant" if it contains ≥1 keyword)
    relevant_chunks = [
        chunk for chunk in retrieved_chunks
        if any(kw.lower() in chunk.lower() for kw in expected_keywords)
    ]
    precision = len(relevant_chunks) / len(retrieved_chunks) if retrieved_chunks else 0.0
    
    # Recall: if we know ground truth relevant count
    if relevant_chunk_count:
        recall = len(relevant_chunks) / relevant_chunk_count
    else:
        recall = precision  # symmetric fallback when ground truth unknown

    # MRR: reciprocal rank of first relevant chunk
    mrr = 0.0
    for rank, chunk in enumerate(retrieved_chunks, 1):
        if any(kw.lower() in chunk.lower() for kw in expected_keywords):
            mrr = 1.0 / rank
            break

    return RetrievalMetrics(
        precision=round(precision, 3),
        recall=round(recall, 3),
        mrr=round(mrr, 3),
        keyword_hit_rate=round(keyword_hit_rate, 3),
    )


def detect_hallucinations(
    ai_response: str,
    unsupported_claims: List[str],
    injection_patterns: Optional[List[str]] = None,
) -> HallucinationMetrics:
    """
    Check an AI response for known unsupported claims and prompt injection patterns.
    
    Args:
        ai_response: The raw AI-generated text.
        unsupported_claims: Specific statements that would be hallucinations.
        injection_patterns: Known injection phrases to detect.
    """
    _DEFAULT_INJECTION_PATTERNS = [
        "ignore previous", "disregard", "you are now",
        "system:", "new instruction", "forget everything",
        "approve this ipo", "certify this", "sebi approved",
    ]
    patterns = injection_patterns or _DEFAULT_INJECTION_PATTERNS

    response_lower = ai_response.lower()

    unsupported_found = sum(
        1 for claim in unsupported_claims
        if claim.lower() in response_lower
    )
    injection_found = sum(
        1 for pattern in patterns
        if pattern.lower() in response_lower
    )

    total = len(unsupported_claims) + len(patterns)
    issues = unsupported_found + injection_found
    hallucination_rate = issues / total if total > 0 else 0.0

    return HallucinationMetrics(
        total_checked=total,
        unsupported_claims_found=unsupported_found,
        hallucination_rate=round(hallucination_rate, 3),
        injection_attempts_detected=injection_found,
    )


def evaluate_drhp_completeness(sections: Dict[str, str]) -> DRHPCompletenessMetrics:
    """
    Evaluate completeness of a generated DRHP.
    
    Args:
        sections: Dict of section_name -> section_content.
    """
    MISSING_MARKERS = ["missing information", "data not provided", "not available", "[missing]", "not disclosed"]
    EVIDENCE_MARKERS = ["according to", "regulation", "icdr", "sebi circular", "clause", "section"]

    total = len(sections)
    with_content = 0
    with_missing = 0
    with_evidence = 0

    for name, content in sections.items():
        if not content or len(content.strip()) < 50:
            continue
        with_content += 1
        content_lower = content.lower()
        if any(marker in content_lower for marker in MISSING_MARKERS):
            with_missing += 1
        if any(marker in content_lower for marker in EVIDENCE_MARKERS):
            with_evidence += 1

    completeness = with_content / total if total > 0 else 0.0

    return DRHPCompletenessMetrics(
        total_sections=total,
        sections_with_content=with_content,
        sections_with_missing_info=with_missing,
        sections_with_evidence=with_evidence,
        completeness_pct=round(completeness * 100, 1),
    )


def compute_overall_score(
    retrieval: RetrievalMetrics,
    hallucination: HallucinationMetrics,
    completeness: DRHPCompletenessMetrics,
) -> float:
    """
    Compute a single weighted AI quality score (0-100).
    
    Weights:
      - Retrieval keyword hit rate: 30%
      - Hallucination rate (inverted): 40%
      - DRHP completeness: 30%
    """
    retrieval_score = retrieval.keyword_hit_rate * 100
    safety_score = (1.0 - hallucination.hallucination_rate) * 100
    completeness_score = completeness.completeness_pct

    overall = (retrieval_score * 0.30) + (safety_score * 0.40) + (completeness_score * 0.30)
    return round(overall, 1)


def generate_evaluation_report(
    retrieved_chunks_per_question: List[List[str]],
    ai_responses: List[str],
    drhp_sections: Dict[str, str],
) -> AIEvaluationReport:
    """
    Run the full evaluation pipeline and return a comprehensive report.
    """
    # Retrieval evaluation: average across all questions
    all_retrieval = []
    for i, q in enumerate(SEBI_EVALUATION_QUESTIONS):
        chunks = retrieved_chunks_per_question[i] if i < len(retrieved_chunks_per_question) else []
        metrics = evaluate_retrieval_quality(q["question"], chunks, q["expected_keywords"])
        all_retrieval.append(metrics)

    avg_retrieval = RetrievalMetrics(
        precision=round(sum(m.precision for m in all_retrieval) / len(all_retrieval), 3),
        recall=round(sum(m.recall for m in all_retrieval) / len(all_retrieval), 3),
        mrr=round(sum(m.mrr for m in all_retrieval) / len(all_retrieval), 3),
        keyword_hit_rate=round(sum(m.keyword_hit_rate for m in all_retrieval) / len(all_retrieval), 3),
    )

    # Hallucination evaluation: aggregate across all responses
    all_hallucination = HallucinationMetrics()
    for i, response in enumerate(ai_responses):
        q = SEBI_EVALUATION_QUESTIONS[i] if i < len(SEBI_EVALUATION_QUESTIONS) else {}
        h = detect_hallucinations(response, q.get("unsupported_claims", []))
        all_hallucination.total_checked += h.total_checked
        all_hallucination.unsupported_claims_found += h.unsupported_claims_found
        all_hallucination.injection_attempts_detected += h.injection_attempts_detected

    if all_hallucination.total_checked > 0:
        all_hallucination.hallucination_rate = round(
            all_hallucination.unsupported_claims_found / all_hallucination.total_checked, 3
        )

    # DRHP completeness
    completeness = evaluate_drhp_completeness(drhp_sections)

    overall = compute_overall_score(avg_retrieval, all_hallucination, completeness)

    return AIEvaluationReport(
        retrieval=avg_retrieval,
        hallucination=all_hallucination,
        completeness=completeness,
        overall_score=overall,
        notes=[
            "Retrieval evaluation uses keyword presence as a proxy for relevance",
            "Hallucination detection is pattern-based, not semantic",
            f"Evaluated {len(SEBI_EVALUATION_QUESTIONS)} SEBI compliance questions",
        ],
    )
