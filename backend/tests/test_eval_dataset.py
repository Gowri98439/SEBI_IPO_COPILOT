"""
test_eval_dataset.py
Tests for the evaluation golden dataset — expanded from 3 to 15 samples.

Coverage targets:
- Schema validation for all EvaluationSample fields
- All 3 intents covered: compliance_check, peer_comparison, general_rag
- must_not_contain non-empty for critical compliance tests
- Negative test samples marked correctly
- No duplicate IDs
- Each sample has meaningful expected_evidence_keywords
"""

import pytest
from app.schemas.drhp_v2 import FinancialRatio  # Ensure schema layer is importable
from tests.eval.dataset import EvaluationSample, GOLDEN_DATASET

# ── Extended golden dataset (15 samples total) ───────────────────────────────
# The original 3 samples are preserved; 12 new samples are added here for testing.

EXTENDED_DATASET = GOLDEN_DATASET + [
    EvaluationSample(
        id="eval-004",
        query="What is the minimum application size for a retail investor in an SME IPO?",
        intent="compliance_check",
        expected_evidence_keywords=["₹1 lakh", "minimum application", "lot size", "retail"],
        expected_regulation_clauses=["Regulation 230"],
        must_not_contain=["₹2 lakh minimum"],
    ),
    EvaluationSample(
        id="eval-005",
        query="What is the role of a Market Maker in an SME IPO?",
        intent="compliance_check",
        expected_evidence_keywords=["market maker", "liquidity", "post-listing", "SME exchange"],
        expected_regulation_clauses=["Regulation 261"],
        must_not_contain=["not required for SME"],
    ),
    EvaluationSample(
        id="eval-006",
        query="How many years of financial statements are required for an SME IPO filing?",
        intent="compliance_check",
        expected_evidence_keywords=["three years", "financial statements", "audited", "preceding"],
        expected_regulation_clauses=["Regulation 228"],
        must_not_contain=["five years", "two years"],
    ),
    EvaluationSample(
        id="eval-007",
        query="What is the minimum post-issue paid-up capital for NSE Emerge listing?",
        intent="compliance_check",
        expected_evidence_keywords=["₹1 crore", "₹25 crore", "paid-up capital", "NSE Emerge"],
        expected_regulation_clauses=["Regulation 229"],
        must_not_contain=["no minimum capital"],
    ),
    EvaluationSample(
        id="eval-008",
        query="Can a company that has changed its name in the last 12 months file for an SME IPO?",
        intent="compliance_check",
        expected_evidence_keywords=["name change", "one year", "last 12 months", "disclosure"],
        expected_regulation_clauses=["Regulation 230"],
        must_not_contain=["name changes are not disclosed"],
    ),
    EvaluationSample(
        id="eval-009",
        query="What is the lock-in period for promoter shareholding post SME IPO?",
        intent="compliance_check",
        expected_evidence_keywords=["lock-in", "3 years", "promoter", "post-issue"],
        expected_regulation_clauses=["Regulation 236", "Schedule XIX"],
        must_not_contain=["no lock-in", "1 year lock"],
    ),
    EvaluationSample(
        id="eval-010",
        query="Compare the EBITDA margin of the company with its listed peers.",
        intent="peer_comparison",
        expected_evidence_keywords=["EBITDA margin", "peer", "industry", "comparison"],
        expected_regulation_clauses=[],
        must_not_contain=["fabricated", "made up"],
    ),
    EvaluationSample(
        id="eval-011",
        query="What is the average P/E ratio for listed SME technology companies?",
        intent="peer_comparison",
        expected_evidence_keywords=["P/E", "price-to-earnings", "SME", "technology", "listed"],
        expected_regulation_clauses=[],
        must_not_contain=["P/E is irrelevant for SMEs"],
    ),
    EvaluationSample(
        id="eval-012",
        query="How does the company's RoNW compare to its peer group?",
        intent="peer_comparison",
        expected_evidence_keywords=["RoNW", "return on net worth", "peer", "benchmark"],
        expected_regulation_clauses=[],
        must_not_contain=["RoNW not applicable"],
    ),
    EvaluationSample(
        id="eval-013",
        query="What are the main risk factors that SEBI expects to be disclosed in a DRHP?",
        intent="general_rag",
        expected_evidence_keywords=["risk factors", "business risks", "financial risks", "regulatory risks", "disclosure"],
        expected_regulation_clauses=["Schedule VI", "Regulation 25"],
        must_not_contain=["no risk factors required"],
    ),
    EvaluationSample(
        id="eval-014",
        query="What disclosures are required regarding related party transactions in an SME IPO?",
        intent="general_rag",
        expected_evidence_keywords=["related party", "transactions", "disclosure", "promoter group"],
        expected_regulation_clauses=["Regulation 26"],
        must_not_contain=["related parties need not be disclosed"],
    ),
    EvaluationSample(
        id="eval-015",
        query="Can a company with pending legal proceedings file for an SME IPO?",
        intent="general_rag",
        expected_evidence_keywords=["legal proceedings", "outstanding litigation", "material", "disclosure"],
        expected_regulation_clauses=["Regulation 26"],
        must_not_contain=["legal proceedings automatically disqualify"],
        is_negative_test=False,
    ),
]


# ── Schema validation ─────────────────────────────────────────────────────────

class TestEvaluationSampleSchema:
    def test_all_samples_have_ids(self):
        for sample in EXTENDED_DATASET:
            assert sample.id and len(sample.id) > 0

    def test_all_ids_are_unique(self):
        ids = [s.id for s in EXTENDED_DATASET]
        assert len(ids) == len(set(ids)), "Duplicate evaluation sample IDs found"

    def test_all_samples_have_query(self):
        for sample in EXTENDED_DATASET:
            assert len(sample.query) > 20, f"Query too short for {sample.id}"

    def test_all_samples_have_intent(self):
        valid_intents = {"compliance_check", "peer_comparison", "general_rag"}
        for sample in EXTENDED_DATASET:
            assert sample.intent in valid_intents, f"{sample.id} has invalid intent: {sample.intent}"

    def test_all_samples_have_expected_keywords(self):
        for sample in EXTENDED_DATASET:
            assert len(sample.expected_evidence_keywords) >= 2, \
                f"{sample.id} needs at least 2 expected_evidence_keywords"

    def test_compliance_checks_have_must_not_contain(self):
        compliance_samples = [s for s in EXTENDED_DATASET if s.intent == "compliance_check"]
        for sample in compliance_samples:
            assert len(sample.must_not_contain) > 0, \
                f"compliance_check {sample.id} must have must_not_contain items"

    def test_compliance_checks_have_regulation_clauses(self):
        compliance_samples = [s for s in EXTENDED_DATASET if s.intent == "compliance_check"]
        for sample in compliance_samples:
            assert len(sample.expected_regulation_clauses) > 0, \
                f"compliance_check {sample.id} must reference a regulation clause"


# ── Dataset coverage ──────────────────────────────────────────────────────────

class TestDatasetCoverage:
    def test_minimum_15_samples(self):
        assert len(EXTENDED_DATASET) >= 15, \
            f"Expected at least 15 samples, got {len(EXTENDED_DATASET)}"

    def test_all_three_intents_represented(self):
        intents = {s.intent for s in EXTENDED_DATASET}
        assert "compliance_check" in intents
        assert "peer_comparison" in intents
        assert "general_rag" in intents

    def test_compliance_check_count(self):
        count = sum(1 for s in EXTENDED_DATASET if s.intent == "compliance_check")
        assert count >= 5, f"Need at least 5 compliance_check samples, got {count}"

    def test_peer_comparison_count(self):
        count = sum(1 for s in EXTENDED_DATASET if s.intent == "peer_comparison")
        assert count >= 3, f"Need at least 3 peer_comparison samples, got {count}"

    def test_general_rag_count(self):
        count = sum(1 for s in EXTENDED_DATASET if s.intent == "general_rag")
        assert count >= 3, f"Need at least 3 general_rag samples, got {count}"

    def test_no_sample_has_empty_must_not_contain_if_negative_test(self):
        negative_tests = [s for s in EXTENDED_DATASET if s.is_negative_test]
        for sample in negative_tests:
            assert len(sample.must_not_contain) > 0, \
                f"Negative test {sample.id} must have must_not_contain"


# ── Original dataset preserved ────────────────────────────────────────────────

class TestOriginalDatasetPreserved:
    def test_eval_001_preserved(self):
        ids = [s.id for s in GOLDEN_DATASET]
        assert "eval-001" in ids

    def test_eval_002_preserved(self):
        ids = [s.id for s in GOLDEN_DATASET]
        assert "eval-002" in ids

    def test_eval_003_preserved(self):
        ids = [s.id for s in GOLDEN_DATASET]
        assert "eval-003" in ids

    def test_eval_001_content(self):
        sample = next(s for s in GOLDEN_DATASET if s.id == "eval-001")
        assert "20%" in sample.expected_evidence_keywords
        assert sample.intent == "general_rag"
