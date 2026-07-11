"""
Golden Evaluation Dataset for IPO Intelligence Platform.
This dataset establishes the baseline for all AI retrieval and generation metrics.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EvaluationSample(BaseModel):
    id: str
    query: str
    intent: str  # e.g., 'compliance_check', 'peer_comparison', 'general_rag'
    expected_evidence_keywords: List[str]
    expected_regulation_clauses: List[str]
    must_not_contain: List[str]
    is_negative_test: bool = False
    
# Golden Dataset
GOLDEN_DATASET: List[EvaluationSample] = [
    EvaluationSample(
        id="eval-001",
        query="What is the minimum promoter contribution required for an SME IPO under SEBI ICDR regulations?",
        intent="general_rag",
        expected_evidence_keywords=["20%", "promoter contribution", "post-issue capital"],
        expected_regulation_clauses=["Regulation 236", "Regulation 236(1)"],
        must_not_contain=["main board", "Regulation 14"] # Regulation 14 is for Main Board
    ),
    EvaluationSample(
        id="eval-002",
        query="Can a company issue shares with superior voting rights in an SME IPO?",
        intent="general_rag",
        expected_evidence_keywords=["superior rights", "equity shares", "SR equity shares"],
        expected_regulation_clauses=["Regulation 227", "Regulation 227(2)"],
        must_not_contain=["yes, without restrictions"]
    ),
    EvaluationSample(
        id="eval-003",
        query="What is the track record requirement for an SME IPO regarding operating profit?",
        intent="general_rag",
        expected_evidence_keywords=["operating profit", "2 out of 3", "preceding three years", "two out of three"],
        expected_regulation_clauses=["Regulation 228"],
        must_not_contain=["net tangible assets of 3 crores"] # Main board condition
    ),
    # Add more as we build out historical comparisons and compliance
]
