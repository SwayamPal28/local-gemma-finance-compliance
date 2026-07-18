import sqlite3
import json
import os
import math
import ai_risk_scorer

DB_PATH = 'compliance.db'

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def load_regulatory_config():
    try:
        with open('regulatory.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {
            'AML_STRUCTURING_THRESHOLD': 10000.0,
            'HIGH_RISK_JURISDICTIONS': ['CYP', 'BHS', 'PAN'],
            'HIGH_VELOCITY_COUNT': 50
        }

def run_rules(*args, **kwargs):
    run_rules_engine()
    return []

def run_rules_engine():
    config = load_regulatory_config()
    aml_thresh = config.get('AML_STRUCTURING_THRESHOLD', 10000)
    structuring_low = aml_thresh * 0.9
    high_velocity = config.get('HIGH_VELOCITY_COUNT', 50)
    
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.create_function('haversine', 4, haversine)
    conn.execute('PRAGMA journal_mode=WAL')
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS feedback_learning (
        account_id TEXT,
        rule_name TEXT,
        suppress_weight REAL,
        PRIMARY KEY (account_id, rule_name)
    )
    """)
    
    try:
        conn.execute("ALTER TABLE case_scores ADD COLUMN expected_roi REAL DEFAULT 0.0")
        conn.execute("ALTER TABLE case_scores ADD COLUMN assigned_queue TEXT DEFAULT 'Tier 1 Support'")
    except Exception:
        pass
        
    try:
        conn.execute("ALTER TABLE kyc_records ADD COLUMN account_type TEXT DEFAULT 'Personal'")
    except Exception:
        pass
        
    print(f"Running rules engine with dynamic threshold: ${aml_thresh}")
    print(f"  High velocity threshold: {high_velocity} transactions")
    
    conn.execute("UPDATE case_scores SET rule_flags = '[]'")
    conn.commit()
    
    feedback_rows = conn.execute("SELECT account_id, rule_name, suppress_weight FROM feedback_learning").fetchall()
    feedback = {}
    for r in feedback_rows:
        feedback.setdefault(r[0], {})[r[1]] = r[2]
        
    print("  Checking High Velocity rule...")
    velocity = conn.execute(f"""
        SELECT sender_id, COUNT(*) as cnt, SUM(amount) as total_vol
        FROM transactions 
        GROUP BY sender_id 
        HAVING cnt > {high_velocity}
    """).fetchall()
    
    print("  Checking Structuring rule...")
    structuring = conn.execute(f"""
        SELECT sender_id, COUNT(*) as cnt 
        FROM transactions 
        WHERE amount >= {structuring_low} AND amount < {aml_thresh} 
        GROUP BY sender_id 
        HAVING cnt >= 3
    """).fetchall()
    
    print("  Checking Large Transaction rule...")
    large_tx = conn.execute("""
        SELECT sender_id, MAX(amount) as max_amt, COUNT(*) as cnt
        FROM transactions 
        WHERE amount > 100000 
        GROUP BY sender_id
    """).fetchall()
    
    print("  Checking Mule Ring (Shared Device) rule...")
    mule_rings = conn.execute("""
        SELECT s.device_id, COUNT(DISTINCT s.account_id) as acc_count, GROUP_CONCAT(DISTINCT s.account_id) as accounts
        FROM sessions s
        GROUP BY s.device_id
        HAVING acc_count > 1
    """).fetchall()
    
    print("  Checking Impossible Travel rule...")
    impossible_travel = conn.execute("""
            SELECT t1.sender_id, s1.city as city1, s2.city as city2, 
                   haversine(s1.location_lat, s1.location_lon, s2.location_lat, s2.location_lon) as dist,
                   (julianday(t2.timestamp) - julianday(t1.timestamp)) * 24 as hours_diff
            FROM transactions t1
            JOIN sessions s1 ON t1.txn_id = s1.txn_id
            JOIN transactions t2 ON t1.sender_id = t2.sender_id AND t1.txn_id != t2.txn_id
            JOIN sessions s2 ON t2.txn_id = s2.txn_id
            WHERE t2.timestamp > t1.timestamp 
              AND (julianday(t2.timestamp) - julianday(t1.timestamp)) * 24 < 12.0
              AND (julianday(t2.timestamp) - julianday(t1.timestamp)) * 24 > 0
              AND haversine(s1.location_lat, s1.location_lon, s2.location_lat, s2.location_lon) > 1000
            GROUP BY t1.sender_id
        """).fetchall()
        
    print("  Checking New Device + High Value rule...")
    new_device_hv = conn.execute("""
            SELECT t.sender_id, s.device_id, t.amount
            FROM transactions t
            JOIN sessions s ON t.txn_id = s.txn_id
            WHERE t.amount > 50000
            AND s.device_id IN (
                SELECT device_id FROM sessions WHERE account_id = t.sender_id GROUP BY device_id HAVING COUNT(*) = 1
            )
            GROUP BY t.sender_id
        """).fetchall()
        
    print("  Checking Circular Transactions rule...")
    self_transfers = conn.execute("""
        SELECT sender_id, COUNT(*) as cnt, SUM(amount) as total
        FROM transactions
        WHERE sender_id = receiver_id
        GROUP BY sender_id
        HAVING cnt >= 2
    """).fetchall()
    
    print("  Checking VPN/Proxy rule...")
    try:
        vpn_sessions = conn.execute("""
            SELECT DISTINCT s.account_id, s.device_id, s.ip_address
            FROM sessions s
            JOIN transactions t ON s.txn_id = t.txn_id
            WHERE s.is_vpn_or_proxy = 1
        """).fetchall()
    except sqlite3.OperationalError:
        vpn_sessions = []
        
    print("  Checking Geo-behavioral baseline drift...")
    try:
        geo_drift = conn.execute("""
            WITH ranked_cities AS (
                SELECT account_id, city, COUNT(*) as city_cnt,
                       ROW_NUMBER() OVER(PARTITION BY account_id ORDER BY COUNT(*) DESC) as rn
                FROM sessions
                WHERE city IS NOT NULL
                GROUP BY account_id, city
            ),
            baseline_city AS (
                SELECT account_id, city as base_city
                FROM ranked_cities
                WHERE rn = 1
            )
            SELECT DISTINCT t.sender_id, s.city as current_city, b.base_city
            FROM transactions t
            JOIN sessions s ON t.txn_id = s.txn_id
            JOIN baseline_city b ON t.sender_id = b.account_id
            WHERE s.city != b.base_city
        """).fetchall()
    except sqlite3.OperationalError:
        geo_drift = []
    
    flags_by_account = {}
    volume_by_account = {}
    
    for acc, cnt, vol in velocity:
        volume_by_account[acc] = max(volume_by_account.get(acc, 0), vol)
        intent = "Expected Operational Volume" if vol > 50000 and cnt < 100 else "Suspected Wash Trading"
        
        flags_by_account.setdefault(acc, []).append({
            'rule': 'High Velocity',
            'reason': f"{cnt} transactions detected (threshold: {high_velocity})",
            'severity': 'high' if cnt > high_velocity * 2 else 'medium',
            'category': 'Operational',
            'intent_attribution': intent
        })
        
    for acc, cnt in structuring:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'Structuring',
            'reason': f"{cnt} transactions just under ${aml_thresh:,.0f} reporting threshold",
            'severity': 'high',
            'category': 'Compliance',
            'intent_attribution': 'Deliberate Obfuscation'
        })
        
    for acc, max_amt, cnt in large_tx:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'Large Transaction',
            'reason': f"{cnt} transaction(s) over $100K (max: ${max_amt:,.0f})",
            'severity': 'high',
            'category': 'Operational',
            'intent_attribution': 'Abnormal Transfer'
        })
        
    for device_id, acc_count, accounts in mule_rings:
        for acc in accounts.split(','):
            flags_by_account.setdefault(acc, []).append({
                'rule': 'Mule Ring (Shared Device)',
                'reason': f"Device {device_id[:12]} is shared across {acc_count} unique accounts.",
                'severity': 'high',
                'category': 'Fraud',
                'intent_attribution': 'Coordinated Mule Network'
            })
            
    for acc, city1, city2, dist, hours_diff in impossible_travel:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'Impossible Travel',
            'reason': f"Login in {city1}, then {city2} ({dist:.0f}km) in {hours_diff:.1f} hours.",
            'severity': 'high',
            'category': 'Fraud',
            'intent_attribution': 'Account Takeover / Stolen Credentials'
        })
        
    for acc, device_id, amount in new_device_hv:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'New Device High Value',
            'reason': f"Unseen device {device_id[:12]} processed ${amount:,.0f}.",
            'severity': 'high',
            'category': 'Fraud',
            'intent_attribution': 'Burner Phone Cash-Out'
        })
        
    for acc, cnt, total in self_transfers:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'Circular Transactions',
            'reason': f"{cnt} self-transfers totaling ${total:,.0f} detected.",
            'severity': 'high',
            'category': 'Fraud',
            'intent_attribution': 'Layering / Wash Trading'
        })
        
    for acc, device_id, ip_address in vpn_sessions:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'VPN/Proxy Usage',
            'reason': f"Transaction initiated from masked IP ({ip_address}) on device {device_id[:12]}.",
            'severity': 'medium',
            'category': 'Fraud',
            'intent_attribution': 'Location Obfuscation'
        })
        
    for acc, current_city, base_city in geo_drift:
        flags_by_account.setdefault(acc, []).append({
            'rule': 'Geo-Behavioral Drift',
            'reason': f"Transaction from {current_city} deviates from baseline {base_city}.",
            'severity': 'medium',
            'category': 'Fraud',
            'intent_attribution': 'Account Takeover / Stolen Credentials'
        })
        
    import risk_scoring
    import consistency
    
    # Retrieve current anomaly scores for accounts to calculate multi-dimensional risk
    anomaly_scores = {}
    try:
        anomaly_rows = conn.execute("SELECT account_id, anomaly_score, case_id FROM case_scores").fetchall()
        for row in anomaly_rows:
            anomaly_scores[row[0]] = {'score': row[1] or 0.0, 'case_id': row[2]}
    except Exception:
        pass
        
    # Apply KYC Consistency checks to all active cases
    for acc, data in anomaly_scores.items():
        case_id = data.get('case_id')
        if not case_id:
            continue
            
        try:
            kyc_data = consistency.check_consistency(case_id)
            if 'mismatches' in kyc_data:
                for mismatch in kyc_data['mismatches']:
                    severity = mismatch.get('evidence', {}).get('severity', 'Medium').lower()
                    category = mismatch.get('evidence', {}).get('category', 'Compliance')
                    flags_by_account.setdefault(acc, []).append({
                        'rule': 'KYC Consistency Mismatch',
                        'reason': mismatch.get('message', ''),
                        'severity': severity,
                        'category': category,
                        'intent_attribution': 'Potential Identity Fraud'
                    })
        except Exception as e:
            print(f"Error checking consistency for {acc}: {e}")
            
    # Combine all known accounts and flagged accounts
    all_accounts = set(anomaly_scores.keys()).union(set(flags_by_account.keys()))
    import random
    
    # Process ALL accounts to ensure risk_score is updated for everyone
    for acc in all_accounts:
        data = anomaly_scores.get(acc, {})
        anomaly = data.get('score', 0.1)
        case_id = data.get('case_id')
        flags = flags_by_account.get(acc, [])
        
        is_new_case = False
        if not case_id:
            case_id = f"CASE_{acc}"
            is_new_case = True
            
        risk_dim = risk_scoring.calculate_multi_dimensional_risk(acc, anomaly, flags)
        
        dimensions = risk_dim.get('dimensions', {})
        max_dim_score = max((d.get('score', 0.0) for d in dimensions.values()), default=0.0) / 100.0
        
        # Calculate features for AI model
        total_rules = len(flags)
        high_sev_count = sum(1 for f in flags if f.get('severity') == 'high')
        
        # Advanced AI Neural Network inference
        overall_risk_score = ai_risk_scorer.predict_risk(
            anomaly_score=anomaly,
            max_dim_score=max_dim_score,
            total_rules=total_rules,
            high_sev_count=high_sev_count
        )
        
        if is_new_case:
            conn.execute("""
                INSERT INTO case_scores (case_id, tenant_id, account_id, anomaly_score, risk_score, risk_dimensions, rule_flags, status, expected_roi, assigned_queue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (case_id, 'tenant_a', acc, anomaly, overall_risk_score, json.dumps(risk_dim), json.dumps(flags), 'OPEN', random.uniform(100.0, 5000.0), 'Triage'))
        else:
            conn.execute("UPDATE case_scores SET rule_flags = ?, risk_dimensions = ?, risk_score = ? WHERE account_id = ?", 
                         (json.dumps(flags), json.dumps(risk_dim), overall_risk_score, acc))
        
    conn.commit()
    conn.close()
    print("Rules engine executed successfully.")
    
if __name__ == '__main__':
    run_rules_engine()
