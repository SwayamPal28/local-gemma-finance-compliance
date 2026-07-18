"""
Database migration: Add enhanced audit_log columns, ocr_documents, platform_settings, 
review_history tables, and seed federated tenant data.
"""
import sqlite3
import json
import random
import hashlib
from datetime import datetime, timedelta

DB = 'compliance.db'

def migrate():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    cur = conn.cursor()

    # ── 1. Enhance audit_log with new columns ──
    existing = [r[1] for r in cur.execute('PRAGMA table_info(audit_log)').fetchall()]
    additions = {
        'reviewer_id': 'TEXT',
        'old_status': 'TEXT',
        'new_status': 'TEXT',
        'ai_recommendation': 'TEXT',
        'risk_score': 'REAL',
    }
    for col, dtype in additions.items():
        if col not in existing:
            cur.execute(f'ALTER TABLE audit_log ADD COLUMN {col} {dtype}')
            print(f"  Added audit_log.{col}")

    # ── 2. OCR Documents table ──
    cur.execute('''CREATE TABLE IF NOT EXISTS ocr_documents (
        doc_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        account_id TEXT,
        doc_type TEXT,
        file_name TEXT,
        extracted_text TEXT,
        parsed_data TEXT,
        confidence REAL,
        matched_at TEXT,
        ai_analysis TEXT
    )''')

    # ── 3. Review History table ──
    cur.execute('''CREATE TABLE IF NOT EXISTS review_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        case_id TEXT,
        reviewer_id TEXT,
        action TEXT,
        old_status TEXT,
        new_status TEXT,
        notes TEXT,
        ai_recommendation TEXT,
        reviewer_confidence INTEGER,
        followed_ai INTEGER,
        time_to_decision_ms INTEGER,
        risk_score REAL,
        timestamp TEXT
    )''')

    # ── 4. Platform settings table ──
    cur.execute('''CREATE TABLE IF NOT EXISTS platform_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT
    )''')

    # Seed default settings
    defaults = {
        'dark_mode': 'true',
        'notifications_enabled': 'true',
        'risk_threshold_high': '0.8',
        'risk_threshold_medium': '0.4',
        'gemma_model': 'gemma3:4b',
        'ollama_url': 'http://localhost:11434',
        'recovery_rate': '0.65',
        'roi_formula': 'risk_score * txn_volume * recovery_rate',
        'review_cost': '75',
        'default_reviewer': 'analyst_01',
    }
    for k, v in defaults.items():
        cur.execute('INSERT OR IGNORE INTO platform_settings (key, value, updated_at) VALUES (?, ?, ?)',
                    (k, v, datetime.utcnow().isoformat()))

    # ── 5. Add multi-tenant data for federated network ──
    tenants = [
        ('tenant_a', 'Antigravity Financial Corp'),
        ('corporate_b', 'Meridian Corporate Bank'),
        ('bank_c', 'Atlas National Bank'),
        ('fintech_d', 'NovaPay Fintech'),
    ]
    cur.execute('''CREATE TABLE IF NOT EXISTS tenants (
        tenant_id TEXT PRIMARY KEY,
        name TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'active'
    )''')
    for tid, tname in tenants:
        cur.execute('INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES (?, ?, ?)',
                    (tid, tname, datetime.utcnow().isoformat()))

    # ── 6. Shared fraud intelligence table ──
    cur.execute('''CREATE TABLE IF NOT EXISTS shared_fraud_intelligence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contributing_tenant TEXT,
        indicator_type TEXT,
        indicator_hash TEXT,
        description TEXT,
        severity TEXT,
        pattern_category TEXT,
        confidence REAL,
        created_at TEXT
    )''')

    # Seed fraud intelligence from tenant_a's real data
    indicators = [
        ('tenant_a', 'BENEFICIARY_PATTERN', 'Shared beneficiary across 3+ accounts with rapid fund movements', 'HIGH', 'Layering', 0.89),
        ('tenant_a', 'VELOCITY_ANOMALY', 'Transaction burst >50 txns in 24h window with decreasing amounts', 'HIGH', 'Structuring', 0.92),
        ('tenant_a', 'GEO_ANOMALY', 'Fund flows to high-risk jurisdictions with no business nexus', 'MEDIUM', 'Sanctions Evasion', 0.78),
        ('corporate_b', 'CIRCULAR_FLOW', 'Funds returning to originator through 2 intermediate entities', 'HIGH', 'Layering', 0.95),
        ('corporate_b', 'INVOICE_MISMATCH', 'Invoice amounts inconsistent with declared business type', 'MEDIUM', 'Trade-Based ML', 0.82),
        ('bank_c', 'DEVICE_SHARING', 'Same device fingerprint across unrelated accounts in 48h', 'HIGH', 'Mule Network', 0.91),
        ('bank_c', 'KYC_VELOCITY', 'Multiple new accounts with similar KYC within 7 days', 'MEDIUM', 'Synthetic Identity', 0.85),
        ('fintech_d', 'CRYPTO_OFFRAMP', 'Fiat-to-crypto pattern with immediate withdrawal to unhosted wallets', 'HIGH', 'Placement', 0.88),
        ('fintech_d', 'SPLIT_DEPOSIT', 'Deposits consistently below reporting threshold ($9,500-$9,999)', 'HIGH', 'Structuring', 0.94),
        ('fintech_d', 'DORMANT_ACTIVATION', 'Long-dormant account suddenly active with high-value international transfers', 'MEDIUM', 'Account Takeover', 0.80),
    ]
    for tenant, itype, desc, sev, cat, conf in indicators:
        h = hashlib.sha256(f"{tenant}:{desc}".encode()).hexdigest()[:16]
        cur.execute('INSERT OR IGNORE INTO shared_fraud_intelligence (contributing_tenant, indicator_type, indicator_hash, description, severity, pattern_category, confidence, created_at) VALUES (?,?,?,?,?,?,?,?)',
                    (tenant, itype, h, desc, sev, cat, conf, datetime.utcnow().isoformat()))

    # ── 7. Seed federated_models for all tenants ──
    import numpy as np
    for tid, _ in tenants:
        cur.execute('INSERT OR IGNORE INTO federated_models (tenant_id, total_amount_mean, total_amount_var, avg_amount_mean, avg_amount_var, tx_count_mean, tx_count_var, anomaly_threshold, last_updated) VALUES (?,?,?,?,?,?,?,?,?)',
                    (tid,
                     random.uniform(50000, 250000), random.uniform(1e8, 1e10),
                     random.uniform(500, 5000), random.uniform(1e4, 1e6),
                     random.uniform(10, 100), random.uniform(50, 500),
                     random.uniform(0.3, 0.7),
                     datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
