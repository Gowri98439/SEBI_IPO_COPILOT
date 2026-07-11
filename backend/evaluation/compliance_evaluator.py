"""
Compliance Evaluator
Calculates Precision, Recall, and F1 metrics for LLM evaluation accuracy against the golden dataset.
"""

def calculate_precision(true_positives: int, false_positives: int) -> float:
    if true_positives + false_positives == 0:
        return 0.0
    return true_positives / (true_positives + false_positives)

def calculate_recall(true_positives: int, false_negatives: int) -> float:
    if true_positives + false_negatives == 0:
        return 0.0
    return true_positives / (true_positives + false_negatives)

def calculate_f1(precision: float, recall: float) -> float:
    if precision + recall == 0.0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)

def evaluate_compliance(results: list[dict]) -> dict:
    """
    results: List of dicts:
    {
       "case_id": "...",
       "expected_status": "pass" | "fail" | "warning",
       "actual_status": "pass" | "fail" | "warning"
    }
    """
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    
    exact_matches = 0
    
    for res in results:
        expected = res["expected_status"]
        actual = res["actual_status"]
        
        if expected == actual:
            exact_matches += 1
            
        # Treat 'fail' and 'warning' as positive flags
        expected_flag = expected in ["fail", "warning"]
        actual_flag = actual in ["fail", "warning"]
        
        if expected_flag and actual_flag:
            true_positives += 1
        elif not expected_flag and not actual_flag:
            true_negatives += 1
        elif actual_flag and not expected_flag:
            false_positives += 1
        elif not actual_flag and expected_flag:
            false_negatives += 1
            
    precision = calculate_precision(true_positives, false_positives)
    recall = calculate_recall(true_positives, false_negatives)
    f1 = calculate_f1(precision, recall)
    
    accuracy = exact_matches / len(results) if results else 0.0
    
    return {
        "accuracy_exact": accuracy,
        "precision_flagging": precision,
        "recall_flagging": recall,
        "f1_flagging": f1,
        "confusion_matrix": {
            "TP": true_positives,
            "FP": false_positives,
            "TN": true_negatives,
            "FN": false_negatives
        }
    }

if __name__ == "__main__":
    sample_results = [
        {"expected_status": "pass", "actual_status": "pass"},
        {"expected_status": "fail", "actual_status": "fail"},
        {"expected_status": "pass", "actual_status": "warning"}, # FP
        {"expected_status": "warning", "actual_status": "pass"}, # FN
    ]
    print("Sample Compliance Evaluation:")
    print(evaluate_compliance(sample_results))
