import sqlite3
from datetime import datetime
import json

DB_PATH = 'compliance.db'

def init_regulatory_tables():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS regulatory_rules (
            rule_id TEXT PRIMARY KEY,
            jurisdiction TEXT,
            rule_type TEXT,
            threshold_value REAL,
            effective_date TEXT,
            description TEXT,
            active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()
    print("Regulatory knowledge tables initialized.")

def sync_regulatory_updates():
    # Mocking a live sync from an external regulatory API
    print("Syncing live regulatory updates (mock)...")
    updates = [
        {"rule_id": "AML_TX_LIMIT_2026", "jurisdiction": "US", "rule_type": "AML_LIMIT", "threshold_value": 8000.0, "description": "New AML transaction reporting limit"},
        {"rule_id": "GST_RATE_TECH_2026", "jurisdiction": "EU", "rule_type": "TAX_RATE", "threshold_value": 0.22, "description": "Revised GST rate for tech services"}
    ]
    
    conn = sqlite3.connect(DB_PATH, timeout=10)
    for u in updates:
        conn.execute('''
            INSERT OR REPLACE INTO regulatory_rules 
            (rule_id, jurisdiction, rule_type, threshold_value, effective_date, description, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (u['rule_id'], u['jurisdiction'], u['rule_type'], u['threshold_value'], datetime.utcnow().isoformat(), u['description']))
    conn.commit()
    conn.close()
    return {"status": "success", "updates_applied": len(updates)}

def evaluate_compliance_shift(case_id, tenant_id='tenant_a'):
    # Re-evaluate a case against the latest rules
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    case = conn.execute("SELECT * FROM case_scores WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
    
    if not case:
        conn.close()
        return {"status": "error", "message": "Case not found"}
        
    active_rules = conn.execute("SELECT * FROM regulatory_rules WHERE active = 1").fetchall()
    conn.close()
    
    shifts = []
    # Mock evaluation logic
    if case['anomaly_score'] > 0.5:
        shifts.append(f"Case anomaly score ({case['anomaly_score']}) violates active dynamic threshold.")
        
    return {
        "case_id": case_id,
        "reevaluation_timestamp": datetime.utcnow().isoformat(),
        "regulatory_shifts_detected": len(shifts),
        "details": shifts
    }

if __name__ == '__main__':
    init_regulatory_tables()
    sync_regulatory_updates()
