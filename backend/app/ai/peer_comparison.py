"""
Peer Comparison Engine
Identifies comparable IPOs and generates benchmarking tables.

DATA INTEGRITY RULES:
- All embedded historical records are labeled SYNTHETIC/DEMONSTRATION DATA
- Selection rationale is transparent and weighted (not pure embedding similarity)
- No synthetic record may be presented as a real verified IPO without proof
- Real data can be injected via DrhpRequestV2.peer_companies (user-supplied)
- If user provides verified peers, those take priority over synthetic dataset
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.schemas.drhp_v2 import DrhpRequestV2, PeerCompany

logger = logging.getLogger(__name__)

MISSING_INFO = "Missing Information"

# ── Embedded synthetic IPO dataset ──────────────────────────────────────────
# IMPORTANT: ALL records below are SYNTHETIC/DEMONSTRATION DATA.
# They are intended to demonstrate the peer comparison engine's structure and
# selection logic. They must NOT be cited in SEBI filings as verified IPO facts.
# Replace with verified data from NSE/BSE exchange filings before production use.

_SYNTHETIC_IPO_DATASET: List[Dict[str, Any]] = [
    {
        "name": "Illustrative Manufacturer A",
        "exchange": "NSE Emerge",
        "sector": "Manufacturing",
        "ipo_year": 2023,
        "issue_size_cr": 35.0,
        "revenue_lakhs": 4800.0,
        "pat_lakhs": 420.0,
        "pat_margin_pct": 8.75,
        "ebitda_margin_pct": 16.2,
        "roe_pct": 18.4,
        "revenue_cagr_3yr_pct": 22.3,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative Manufacturer B",
        "exchange": "BSE SME",
        "sector": "Manufacturing",
        "ipo_year": 2022,
        "issue_size_cr": 28.0,
        "revenue_lakhs": 3200.0,
        "pat_lakhs": 280.0,
        "pat_margin_pct": 8.75,
        "ebitda_margin_pct": 14.8,
        "roe_pct": 21.2,
        "revenue_cagr_3yr_pct": 18.7,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative IT Services A",
        "exchange": "NSE Emerge",
        "sector": "Technology & IT",
        "ipo_year": 2023,
        "issue_size_cr": 42.0,
        "revenue_lakhs": 2800.0,
        "pat_lakhs": 420.0,
        "pat_margin_pct": 15.0,
        "ebitda_margin_pct": 22.4,
        "roe_pct": 27.8,
        "revenue_cagr_3yr_pct": 35.6,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative Healthcare A",
        "exchange": "BSE SME",
        "sector": "Healthcare & Pharma",
        "ipo_year": 2022,
        "issue_size_cr": 55.0,
        "revenue_lakhs": 8500.0,
        "pat_lakhs": 595.0,
        "pat_margin_pct": 7.0,
        "ebitda_margin_pct": 18.6,
        "roe_pct": 15.2,
        "revenue_cagr_3yr_pct": 14.2,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative FMCG / Retail A",
        "exchange": "NSE Emerge",
        "sector": "Retail & FMCG",
        "ipo_year": 2021,
        "issue_size_cr": 18.0,
        "revenue_lakhs": 6200.0,
        "pat_lakhs": 186.0,
        "pat_margin_pct": 3.0,
        "ebitda_margin_pct": 9.8,
        "roe_pct": 12.6,
        "revenue_cagr_3yr_pct": 11.4,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative Infrastructure A",
        "exchange": "BSE SME",
        "sector": "Infrastructure & Logistics",
        "ipo_year": 2023,
        "issue_size_cr": 75.0,
        "revenue_lakhs": 12000.0,
        "pat_lakhs": 720.0,
        "pat_margin_pct": 6.0,
        "ebitda_margin_pct": 13.5,
        "roe_pct": 14.8,
        "revenue_cagr_3yr_pct": 16.9,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative Chemical A",
        "exchange": "NSE Emerge",
        "sector": "Chemicals & Specialty",
        "ipo_year": 2022,
        "issue_size_cr": 48.0,
        "revenue_lakhs": 7600.0,
        "pat_lakhs": 684.0,
        "pat_margin_pct": 9.0,
        "ebitda_margin_pct": 17.2,
        "roe_pct": 19.4,
        "revenue_cagr_3yr_pct": 24.8,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative Textile A",
        "exchange": "BSE SME",
        "sector": "Textiles & Apparel",
        "ipo_year": 2021,
        "issue_size_cr": 22.0,
        "revenue_lakhs": 4100.0,
        "pat_lakhs": 246.0,
        "pat_margin_pct": 6.0,
        "ebitda_margin_pct": 11.8,
        "roe_pct": 16.2,
        "revenue_cagr_3yr_pct": 12.1,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative AgriTech A",
        "exchange": "NSE Emerge",
        "sector": "Agriculture & Agro-processing",
        "ipo_year": 2023,
        "issue_size_cr": 31.0,
        "revenue_lakhs": 5400.0,
        "pat_lakhs": 378.0,
        "pat_margin_pct": 7.0,
        "ebitda_margin_pct": 14.4,
        "roe_pct": 17.6,
        "revenue_cagr_3yr_pct": 19.3,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
    {
        "name": "Illustrative Financial Services A",
        "exchange": "BSE SME",
        "sector": "Financial Services",
        "ipo_year": 2023,
        "issue_size_cr": 62.0,
        "revenue_lakhs": 3800.0,
        "pat_lakhs": 570.0,
        "pat_margin_pct": 15.0,
        "ebitda_margin_pct": 28.6,
        "roe_pct": 22.4,
        "revenue_cagr_3yr_pct": 28.1,
        "data_source": "SYNTHETIC/DEMONSTRATION DATA",
        "data_verified": False,
    },
]


# ── Similarity scoring ────────────────────────────────────────────────────────

def _score_similarity(
    target_req: DrhpRequestV2,
    peer: Dict[str, Any],
) -> float:
    """
    Compute a transparent weighted similarity score between the target company
    and a peer candidate. Returns 0.0–1.0.

    Weight breakdown (total = 1.0):
    - Sector match:            0.40 (most important — same industry dynamics)
    - Revenue scale match:     0.25 (similar scale companies have similar valuation metrics)
    - Issue size match:        0.20 (comparable IPO size)
    - IPO vintage match:       0.10 (recency of comparable)
    - PAT margin proximity:    0.05
    """
    score = 0.0
    latest_fy = target_req.financials[-1] if target_req.financials else None

    # 1. Sector match (0.40)
    target_sector = target_req.company.sector.lower().strip()
    peer_sector = peer.get("sector", "").lower().strip()
    if target_sector == peer_sector:
        score += 0.40
    elif any(word in peer_sector for word in target_sector.split()):
        score += 0.20  # Partial sector match

    # 2. Revenue scale match (0.25) — within 3x is a good comparable
    if latest_fy and latest_fy.revenue and peer.get("revenue_lakhs"):
        target_rev = latest_fy.revenue
        peer_rev = peer["revenue_lakhs"]
        ratio = max(target_rev, peer_rev) / max(min(target_rev, peer_rev), 1.0)
        if ratio <= 1.5:
            score += 0.25
        elif ratio <= 3.0:
            score += 0.15
        elif ratio <= 5.0:
            score += 0.05

    # 3. Issue size match (0.20) — within 2x
    target_size = target_req.issue.issue_size_cr
    peer_size = peer.get("issue_size_cr", 0)
    if target_size and peer_size:
        ratio = max(target_size, peer_size) / max(min(target_size, peer_size), 1.0)
        if ratio <= 1.5:
            score += 0.20
        elif ratio <= 2.5:
            score += 0.10
        elif ratio <= 5.0:
            score += 0.05

    # 4. Recency (0.10) — prefer recent IPOs
    ipo_year = peer.get("ipo_year", 0)
    if ipo_year >= 2022:
        score += 0.10
    elif ipo_year >= 2020:
        score += 0.05

    # 5. PAT margin proximity (0.05)
    if latest_fy and latest_fy.revenue and latest_fy.net_profit is not None:
        target_margin = (latest_fy.net_profit / latest_fy.revenue) * 100
        peer_margin = peer.get("pat_margin_pct", None)
        if peer_margin is not None:
            diff = abs(target_margin - peer_margin)
            if diff <= 3:
                score += 0.05
            elif diff <= 7:
                score += 0.02

    return round(min(score, 1.0), 4)


def _explain_selection(
    target_req: DrhpRequestV2,
    peer: Dict[str, Any],
    score: float,
) -> str:
    """Generate a plain-language explanation of why this peer was selected."""
    reasons = []
    target_sector = target_req.company.sector.lower()
    peer_sector = peer.get("sector", "").lower()
    latest_fy = target_req.financials[-1] if target_req.financials else None

    if target_sector == peer_sector:
        reasons.append(f"same sector ({peer.get('sector', 'N/A')})")
    elif any(word in peer_sector for word in target_sector.split()):
        reasons.append(f"adjacent sector ({peer.get('sector', 'N/A')})")

    if latest_fy and latest_fy.revenue and peer.get("revenue_lakhs"):
        ratio = max(latest_fy.revenue, peer["revenue_lakhs"]) / max(min(latest_fy.revenue, peer["revenue_lakhs"]), 1)
        if ratio <= 3.0:
            reasons.append(f"comparable revenue scale (~{peer['revenue_lakhs']:,.0f} Lakhs vs target)")

    target_size = target_req.issue.issue_size_cr
    peer_size = peer.get("issue_size_cr", 0)
    if target_size and peer_size and max(target_size, peer_size) / max(min(target_size, peer_size), 1) <= 2.5:
        reasons.append(f"comparable issue size (₹{peer_size:.0f} Cr)")

    ipo_year = peer.get("ipo_year", 0)
    if ipo_year >= 2021:
        reasons.append(f"recent IPO ({ipo_year})")

    if not reasons:
        reasons.append("best available match in synthetic dataset")

    return "; ".join(reasons).capitalize() + f" [Similarity: {score:.0%}]"


# ── Main peer comparison function ─────────────────────────────────────────────

def find_comparable_peers(req: DrhpRequestV2) -> List[PeerCompany]:
    """
    Find the most comparable IPOs for benchmarking.

    Priority:
    1. User-provided peer companies (DrhpRequestV2.peer_companies)
    2. Synthetic demonstration dataset (clearly labeled)

    Returns top N peers sorted by similarity score (descending).
    """
    max_peers = req.max_peers or 5

    # If user supplied verified peers, use those first
    user_peers = req.peer_companies or []
    if len(user_peers) >= max_peers:
        logger.info("Using %d user-provided peer companies", len(user_peers))
        return user_peers[:max_peers]

    # Score all synthetic peers
    scored: List[tuple[float, Dict[str, Any]]] = []
    for peer in _SYNTHETIC_IPO_DATASET:
        score = _score_similarity(req, peer)
        scored.append((score, peer))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Fill remaining slots from synthetic dataset
    remaining_slots = max_peers - len(user_peers)
    selected_synthetic = scored[:remaining_slots]

    result = list(user_peers)  # Start with user-provided
    for score, peer_dict in selected_synthetic:
        rationale = _explain_selection(req, peer_dict, score)
        result.append(PeerCompany(
            name=peer_dict["name"],
            exchange=peer_dict.get("exchange", "NSE/BSE SME"),
            sector=peer_dict.get("sector", "N/A"),
            ipo_year=peer_dict.get("ipo_year"),
            issue_size_cr=peer_dict.get("issue_size_cr"),
            revenue_lakhs=peer_dict.get("revenue_lakhs"),
            pat_lakhs=peer_dict.get("pat_lakhs"),
            pat_margin_pct=peer_dict.get("pat_margin_pct"),
            ebitda_margin_pct=peer_dict.get("ebitda_margin_pct"),
            roe_pct=peer_dict.get("roe_pct"),
            revenue_cagr_3yr_pct=peer_dict.get("revenue_cagr_3yr_pct"),
            data_source=peer_dict.get("data_source", "SYNTHETIC/DEMONSTRATION DATA"),
            data_verified=peer_dict.get("data_verified", False),
            similarity_score=score,
            selection_rationale=rationale,
        ))

    logger.info(
        "Peer comparison: %d total peers selected (%d user-provided, %d synthetic)",
        len(result),
        len(user_peers),
        len(selected_synthetic),
    )
    return result


def build_peer_comparison_table(
    req: DrhpRequestV2,
    peers: List[PeerCompany],
) -> List[Dict[str, Any]]:
    """
    Build a structured comparison table: target company vs all peers.
    Each row is a dict with company name + key metrics.
    """
    latest_fy = req.financials[-1] if req.financials else None
    target_pat_margin = None
    if latest_fy and latest_fy.revenue and latest_fy.net_profit is not None and latest_fy.revenue > 0:
        target_pat_margin = round((latest_fy.net_profit / latest_fy.revenue) * 100, 2)

    rows = []

    # Target company row
    rows.append({
        "company": f"{req.company.name} (This Company)",
        "exchange": req.issue.merchant_banker or "—",
        "sector": req.company.sector,
        "ipo_year": "Current",
        "issue_size_cr": req.issue.issue_size_cr,
        "revenue_lakhs": latest_fy.revenue if latest_fy else None,
        "pat_margin_pct": target_pat_margin,
        "ebitda_margin_pct": (
            round((latest_fy.ebitda / latest_fy.revenue) * 100, 2)
            if latest_fy and latest_fy.ebitda and latest_fy.revenue
            else None
        ),
        "roe_pct": None,  # Computed separately in financial_intelligence
        "revenue_cagr_3yr_pct": None,  # Computed separately
        "data_source": "Company Submission",
        "is_target": True,
    })

    for peer in peers:
        rows.append({
            "company": peer.name,
            "exchange": peer.exchange,
            "sector": peer.sector,
            "ipo_year": peer.ipo_year,
            "issue_size_cr": peer.issue_size_cr,
            "revenue_lakhs": peer.revenue_lakhs,
            "pat_margin_pct": peer.pat_margin_pct,
            "ebitda_margin_pct": peer.ebitda_margin_pct,
            "roe_pct": peer.roe_pct,
            "revenue_cagr_3yr_pct": peer.revenue_cagr_3yr_pct,
            "data_source": peer.data_source,
            "similarity_score": peer.similarity_score,
            "selection_rationale": peer.selection_rationale,
            "is_target": False,
        })

    return rows


def compute_peer_statistics(table: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute sector median/mean/max for each metric across peers (excluding target)."""
    peers_only = [r for r in table if not r.get("is_target", False)]

    def _stat(key: str) -> Dict[str, Optional[float]]:
        vals = [r[key] for r in peers_only if r.get(key) is not None]
        if not vals:
            return {"median": None, "mean": None, "max": None, "min": None}
        return {
            "median": sorted(vals)[len(vals) // 2],
            "mean": sum(vals) / len(vals),
            "max": max(vals),
            "min": min(vals),
        }

    return {
        "pat_margin_pct": _stat("pat_margin_pct"),
        "ebitda_margin_pct": _stat("ebitda_margin_pct"),
        "roe_pct": _stat("roe_pct"),
        "revenue_cagr_3yr_pct": _stat("revenue_cagr_3yr_pct"),
        "issue_size_cr": _stat("issue_size_cr"),
        "data_disclaimer": "SYNTHETIC/DEMONSTRATION DATA — not verified from exchange filings. "
                           "Replace with verified NSE/BSE SME IPO data before SEBI filing.",
    }
