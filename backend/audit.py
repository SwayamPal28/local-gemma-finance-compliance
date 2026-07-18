"""Immutable audit logging with full provenance tracking."""
import sqlite3
import datetime
import json

DB_PATH = 'compliance.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn

def log_event(tenant_id, case_id, action, notes='', reviewer_id='analyst_01',
              old_status='', new_status='', ai_recommendation='', risk_score=0.0, conn=None):
    """Insert an immutable audit event capturing full provenance."""
    close_conn = False
    if conn is None:
        conn = get_conn()
        close_conn = True
    conn.execute('''INSERT INTO audit_log 
        (tenant_id, case_id, event_time, reviewer_action, notes,
         reviewer_id, old_status, new_status, ai_recommendation, risk_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (tenant_id, case_id, datetime.datetime.utcnow().isoformat(), action, notes,
         reviewer_id, old_status, new_status, ai_recommendation, risk_score))
    if close_conn:
        conn.commit()
        conn.close()

def get_audit_logs(tenant_id=None, case_id=None, action=None, search=None, limit=500):
    """Retrieve audit logs with optional filters."""
    conn = get_conn()
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if tenant_id:
        query += " AND tenant_id = ?"
        params.append(tenant_id)
    if case_id:
        query += " AND case_id = ?"
        params.append(case_id)
    if action:
        query += " AND reviewer_action LIKE ?"
        params.append(f"%{action}%")
    if search:
        query += " AND (notes LIKE ? OR case_id LIKE ? OR reviewer_action LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    query += " ORDER BY event_time DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_case_timeline(case_id):
    """Get complete timeline for a single case."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE case_id = ? ORDER BY event_time ASC", (case_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
