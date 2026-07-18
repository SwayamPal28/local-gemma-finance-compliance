import sqlite3

DB_PATH = 'compliance.db'

def calculate_case_roi(case):
    """
    Combines monetary impact, anomaly score (probability of fraud), 
    and estimated investigation cost to calculate an ROI score.
    """
    base_impact = case.get('expected_roi', 0.0)
    anomaly_score = case.get('anomaly_score', 0.0)
    risk_score = case.get('risk_score', 0.0) / 100.0
    
    # Simple cost heuristic: high complexity cases cost more to review
    # We estimate $50 per review hour, standard case = 1 hour, high risk = 2.5 hours
    cost_estimate = 50.0 * (1.0 + risk_score * 1.5)
    
    # ROI = (Probability of Fraud * Monetary Impact) - Investigation Cost
    calculated_roi = (anomaly_score * base_impact * 10.0) - cost_estimate
    return max(0.0, calculated_roi)

def rank_queue_by_roi(cases):
    """
    Rank review cases by investigation cost vs. probability of fraud vs. monetary impact
    """
    for case in cases:
        case['calculated_roi'] = calculate_case_roi(case)
        
    # Sort descending by ROI
    sorted_cases = sorted(cases, key=lambda x: x['calculated_roi'], reverse=True)
    return sorted_cases
