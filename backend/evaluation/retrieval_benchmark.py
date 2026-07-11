"""
Retrieval Benchmark Evaluator
Calculates MRR (Mean Reciprocal Rank) and Hit@K metrics for RAG retrieval against the golden dataset.
"""

def calculate_mrr(rankings: list[int]) -> float:
    """
    Calculate Mean Reciprocal Rank.
    `rankings` is a list of the 1-based ranks of the first relevant document for a set of queries.
    If no relevant document was retrieved for a query, the rank is considered 0 or infinity (reciprocal is 0).
    """
    if not rankings:
        return 0.0
    reciprocal_ranks = [1.0 / rank if rank > 0 else 0.0 for rank in rankings]
    return sum(reciprocal_ranks) / len(rankings)

def calculate_hit_at_k(rankings: list[int], k: int) -> float:
    """
    Calculate Hit@K metric.
    Percentage of queries where the relevant document was retrieved in the top K results.
    """
    if not rankings:
        return 0.0
    hits = sum(1 for rank in rankings if 0 < rank <= k)
    return hits / len(rankings)

def evaluate_retrieval(results: list[dict]) -> dict:
    """
    results: List of dicts, each containing:
    {
       "case_id": "...",
       "rank_of_expected": int # 0 if not found
    }
    """
    rankings = [res.get("rank_of_expected", 0) for res in results]
    
    return {
        "mrr": calculate_mrr(rankings),
        "hit_at_1": calculate_hit_at_k(rankings, 1),
        "hit_at_3": calculate_hit_at_k(rankings, 3),
        "hit_at_5": calculate_hit_at_k(rankings, 5),
        "hit_at_10": calculate_hit_at_k(rankings, 10),
    }

if __name__ == "__main__":
    # Example usage / sanity check
    sample_ranks = [1, 3, 0, 5, 2] # 5 queries, one missed completely
    print("Sample Retrieval Evaluation:")
    print(evaluate_retrieval([{"rank_of_expected": r} for r in sample_ranks]))
