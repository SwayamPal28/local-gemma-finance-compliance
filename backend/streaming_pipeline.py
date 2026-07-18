import sqlite3
import time
from datetime import datetime
import json

def init_streaming_tables():
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute("""
    CREATE TABLE IF NOT EXISTS temporal_constraints (
        constraint_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        constraint_type TEXT,
        doc_a_type TEXT,
        doc_b_type TEXT,
        max_delay_hours INTEGER,
        violation_severity TEXT,
        active INTEGER DEFAULT 1
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS document_arrivals (
        arrival_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        document_type TEXT,
        document_id TEXT,
        account_id TEXT,
        arrived_at TEXT,
        expected_arrival_window_start TEXT,
        expected_arrival_window_end TEXT,
        is_late INTEGER,
        lateness_seconds INTEGER,
        processed INTEGER DEFAULT 0,
        triggered_reconciliation INTEGER DEFAULT 0
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS reconciliation_triggers (
        trigger_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        case_id TEXT,
        account_id TEXT,
        trigger_reason TEXT,
        severity TEXT,
        triggered_at TEXT,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()

def setup_default_temporal_constraints():
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute("""
        INSERT OR IGNORE INTO temporal_constraints
        (constraint_id, tenant_id, constraint_type, doc_a_type, doc_b_type, max_delay_hours, violation_severity, active)
        VALUES 
        ('TEMP_001', 'tenant_a', 'kyc_before_transaction', 'kyc', 'transaction', 0, 'high', 1),
        ('TEMP_002', 'tenant_a', 'invoice_before_payment', 'invoice', 'transaction', 48, 'medium', 1)
    """)
    conn.commit()
    conn.close()

def ingest_document(req):
    # Expected req: tenant_id, document_type, document_id, account_id, document_data, expected_arrival_time
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    
    arrival_id = f"ARR_{req.document_id}_{int(time.time())}"
    arrived_at = datetime.utcnow()
    
    expected_end = None
    is_late = 0
    lateness_seconds = 0
    
    if req.expected_arrival_time:
        expected_end = datetime.fromisoformat(req.expected_arrival_time)
        if arrived_at > expected_end:
            is_late = 1
            lateness_seconds = int((arrived_at - expected_end).total_seconds())

    conn.execute("""
        INSERT INTO document_arrivals
        (arrival_id, tenant_id, document_type, document_id, account_id, arrived_at, expected_arrival_window_end, is_late, lateness_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (arrival_id, req.tenant_id, req.document_type, req.document_id, req.account_id, arrived_at.isoformat(), req.expected_arrival_time, is_late, lateness_seconds))
    
    # Check temporal constraints
    constraints = conn.execute("SELECT * FROM temporal_constraints WHERE tenant_id = ? AND doc_b_type = ? AND active = 1", (req.tenant_id, req.document_type)).fetchall()
    
    reconciliation_triggered = False
    for c in constraints:
        # Check if doc_a exists
        doc_a = conn.execute("SELECT * FROM document_arrivals WHERE account_id = ? AND document_type = ? AND tenant_id = ? ORDER BY arrived_at DESC LIMIT 1", (req.account_id, c['doc_a_type'], req.tenant_id)).fetchone()
        
        if not doc_a:
            # Violation: doc_b arrived before doc_a
            conn.execute("INSERT INTO reconciliation_triggers (tenant_id, account_id, trigger_reason, severity, triggered_at, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (req.tenant_id, req.account_id, f"Temporal constraint violation: Missing prerequisite document {c['doc_a_type']}", c['violation_severity'], arrived_at.isoformat(), 'PENDING'))
            reconciliation_triggered = True
            
    if reconciliation_triggered:
        conn.execute("UPDATE document_arrivals SET triggered_reconciliation = 1 WHERE arrival_id = ?", (arrival_id,))
    
    conn.commit()
    conn.close()
    return {"status": "success", "arrival_id": arrival_id, "is_late": is_late, "reconciliation_triggered": reconciliation_triggered}

def get_streaming_stats(tenant_id):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    
    stats = {}
    stats['total_documents_arrived'] = conn.execute("SELECT COUNT(*) as cnt FROM document_arrivals WHERE tenant_id = ?", (tenant_id,)).fetchone()['cnt']
    stats['late_arrivals'] = conn.execute("SELECT COUNT(*) as cnt FROM document_arrivals WHERE tenant_id = ? AND is_late = 1", (tenant_id,)).fetchone()['cnt']
    stats['total_reconciliations_triggered'] = conn.execute("SELECT COUNT(*) as cnt FROM reconciliation_triggers WHERE tenant_id = ?", (tenant_id,)).fetchone()['cnt']
    stats['pending_reconciliations'] = conn.execute("SELECT COUNT(*) as cnt FROM reconciliation_triggers WHERE tenant_id = ? AND status = 'PENDING'", (tenant_id,)).fetchone()['cnt']
    
    # get recent arrivals
    stats['recent_arrivals'] = [dict(r) for r in conn.execute("SELECT * FROM document_arrivals WHERE tenant_id = ? ORDER BY arrived_at DESC LIMIT 10", (tenant_id,)).fetchall()]
    
    conn.close()
    return stats

if __name__ == '__main__':
    init_streaming_tables()
    setup_default_temporal_constraints()
    print("Streaming pipeline initialized.")
