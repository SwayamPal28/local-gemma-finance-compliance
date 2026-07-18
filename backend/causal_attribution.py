import sqlite3
from datetime import datetime
import random

DB_PATH = 'compliance.db'

def init_causal_tables():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS causal_analysis (
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            tenant_id TEXT,
            discrepancy_type TEXT,
            inferred_intent TEXT,
            confidence REAL,
            causal_path TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Causal attribution tables initialized.")

def infer_causal_intent(case_id, tenant_id='tenant_a'):
    """
    Distinguish between operational lag and deliberate omission.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    case = conn.execute("SELECT * FROM case_scores WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
    
    if not case:
        conn.close()
        return {"status": "error", "message": "Case not found"}

    # Mocking causal inference over cross-document timelines
    discrepancy = "Missing Invoice Match"
    intent = "operational_lag" if random.random() > 0.4 else "deliberate_omission"
    confidence = round(random.uniform(0.65, 0.98), 2)
    path = "Invoice received -> Payment delayed -> Cross-border lag inferred" if intent == 'operational_lag' else "Invoice received -> Payment missing -> Shell company node detected"
    
    conn.execute('''
        INSERT INTO causal_analysis (case_id, tenant_id, discrepancy_type, inferred_intent, confidence, causal_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (case_id, tenant_id, discrepancy, intent, confidence, path, datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()
    
    return {
        "case_id": case_id,
        "discrepancy": discrepancy,
        "inferred_intent": intent,
        "confidence": confidence,
        "causal_path": path
    }

if __name__ == '__main__':
    init_causal_tables()
