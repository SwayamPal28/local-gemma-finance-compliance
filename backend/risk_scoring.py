import json

DEFAULT_THRESHOLDS = {
    'fraud': 70.0,
    'compliance': 65.0,
    'operational': 80.0
}

def calculate_multi_dimensional_risk(account_id, anomaly_score, rule_flags):
    """
    Aggregates inputs into separate scores for Fraud, Compliance, and Operational risks.
    Also separates into Session and Transaction risk components.
    """
    scores = {
        'fraud': {'score': 0.0, 'reasons': []},
        'compliance': {'score': 0.0, 'reasons': []},
        'operational': {'score': 0.0, 'reasons': []},
        'session_risk': {'score': 0.0, 'reasons': []},
        'transaction_risk': {'score': 0.0, 'reasons': []}
    }
    
    # Base risk from anomaly score (distributed across dimensions as a baseline)
    base_score = min(anomaly_score * 50, 40) # capping base score contribution at 40
    scores['fraud']['score'] += base_score * 0.5
    scores['compliance']['score'] += base_score * 0.3
    scores['operational']['score'] += base_score * 0.2
    
    if anomaly_score > 0.5:
        scores['fraud']['reasons'].append(f"High baseline anomaly detected (score: {anomaly_score:.2f})")
        
    for flag in rule_flags:
        category = flag.get('category', '').lower()
        severity = flag.get('severity', 'low')
        rule_name = flag.get('rule', 'Unknown Rule')
        reason = flag.get('reason', '')
        
        weight = 30 if severity == 'high' else (15 if severity == 'medium' else 5)
        
        # Categorize rules
        if 'fraud' in category or 'mule' in rule_name.lower() or 'takeover' in flag.get('intent_attribution', '').lower() or rule_name == 'New Device High Value' or rule_name == 'Impossible Travel':
            scores['fraud']['score'] += weight
            scores['fraud']['reasons'].append(f"{rule_name}: {reason} (+{weight} fraud risk)")
        elif 'compliance' in category or 'structuring' in rule_name.lower():
            scores['compliance']['score'] += weight
            scores['compliance']['reasons'].append(f"{rule_name}: {reason} (+{weight} compliance risk)")
        else:
            scores['operational']['score'] += weight
            scores['operational']['reasons'].append(f"{rule_name}: {reason} (+{weight} operational risk)")
            
        # Session vs Transaction risk categorization
        session_rules = ['Mule Ring (Shared Device)', 'Impossible Travel', 'New Device High Value', 'VPN/Proxy Usage', 'Geo-Behavioral Drift']
        
        if rule_name in session_rules:
            scores['session_risk']['score'] += weight
            scores['session_risk']['reasons'].append(f"{rule_name}: {reason} (+{weight} session risk)")
        else:
            scores['transaction_risk']['score'] += weight
            scores['transaction_risk']['reasons'].append(f"{rule_name}: {reason} (+{weight} transaction risk)")

    # Normalize scores to 0-100 and calculate confidence
    total_flags = len(rule_flags)
    confidence = min(50 + (total_flags * 10), 95) # simple confidence heuristic
    
    for dim in scores:
        scores[dim]['score'] = min(scores[dim]['score'], 100.0)
        
    return {
        'dimensions': scores,
        'confidence_score': confidence
    }

def evaluate_escalation(risk_dimensions, custom_thresholds=None):
    """
    Determines if the case crosses the user-adjusted escalation threshold.
    """
    thresholds = custom_thresholds or DEFAULT_THRESHOLDS
    escalations = []
    
    scores = risk_dimensions.get('dimensions', {})
    
    for dim, data in scores.items():
        if dim in thresholds and data['score'] >= thresholds[dim]:
            escalations.append({
                'dimension': dim,
                'score': data['score'],
                'threshold': thresholds[dim]
            })
            
    return {
        'requires_escalation': len(escalations) > 0,
        'escalation_details': escalations
    }
