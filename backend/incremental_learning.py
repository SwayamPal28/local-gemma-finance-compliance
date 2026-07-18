import sqlite3
from datetime import datetime

DB_PATH = 'compliance.db'

def init_feedback_tables():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reviewer_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            tenant_id TEXT,
            field_name TEXT,
            expected_value TEXT,
            correction_notes TEXT,
            timestamp TEXT,
            applied_to_model INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("Incremental learning tables initialized.")

def log_correction(case_id, tenant_id, field_name, expected_value, notes):
    """
    Log a reviewer correction to be used for incremental few-shot learning.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('''
        INSERT INTO reviewer_feedback (case_id, tenant_id, field_name, expected_value, correction_notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (case_id, tenant_id, field_name, expected_value, notes, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"status": "logged", "case_id": case_id}

def adapt_model_incrementally(tenant_id):
    """
    Simulate updating the model with few-shot examples from recent feedback.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    unapplied = conn.execute("SELECT count(*) FROM reviewer_feedback WHERE tenant_id = ? AND applied_to_model = 0", (tenant_id,)).fetchone()[0]
    
    if unapplied > 0:
        print(f"Adapting local model for {tenant_id} using {unapplied} new feedback examples...")
        # Mark as applied
        conn.execute("UPDATE reviewer_feedback SET applied_to_model = 1 WHERE tenant_id = ? AND applied_to_model = 0", (tenant_id,))
        conn.commit()
        status = f"Adapted model with {unapplied} examples."
    else:
        status = "No new feedback to adapt."
        
    conn.close()
    return {"status": "success", "message": status}

if __name__ == '__main__':
    init_feedback_tables()
