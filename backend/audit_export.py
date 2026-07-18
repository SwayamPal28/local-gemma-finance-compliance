import sqlite3
import os
from datetime import datetime

def init_provenance_tables():
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute("""
    CREATE TABLE IF NOT EXISTS provenance_chains (
        provenance_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        case_id TEXT,
        snapshot_timestamp TEXT,
        data_snapshot_hash TEXT,ss
        model_version TEXT,
        regulatory_config_hash TEXT,
        input_data_hash TEXT,
        output_hash TEXT,
        reproducible INTEGER DEFAULT 1,
        FOREIGN KEY(case_id) REFERENCES case_scores(case_id)
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS decision_lineage (
        lineage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        provenance_id TEXT,
        tenant_id TEXT,
        case_id TEXT,
        step_number INTEGER,
        step_type TEXT,
        step_timestamp TEXT,
        input_snapshot TEXT,
        output_snapshot TEXT,
        model_params TEXT,
        execution_time_ms INTEGER
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_exports (
        export_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        case_ids TEXT,
        export_format TEXT,
        exported_at TEXT,
        exported_by TEXT,
        file_path TEXT,
        file_hash TEXT,
        includes_full_provenance INTEGER
    )
    """)
    conn.commit()
    conn.close()
    print("Provenance tracking tables initialized.")

def export_audit_ready_case(case_id, tenant_id):
    print(f"Exporting audit case {case_id} for {tenant_id}")
    import hashlib
    try:
        from fpdf import FPDF
    except ImportError:
        return {"status": "error", "message": "fpdf not installed"}

    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    
    case = conn.execute("SELECT * FROM compliance_cases WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        return {"status": "error", "message": "Case not found"}

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Audit Report: {case_id}", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Tenant: {tenant_id}", ln=1, align='L')
    pdf.cell(200, 10, txt=f"Generated: {datetime.utcnow().isoformat()}", ln=1, align='L')
    pdf.line(10, 40, 200, 40)
    pdf.ln(10)
    
    pdf.cell(200, 10, txt=f"Account ID: {case['account_id']}", ln=1, align='L')
    pdf.cell(200, 10, txt=f"Status: {case['status']}", ln=1, align='L')
    
    scores = conn.execute("SELECT * FROM case_scores WHERE case_id = ?", (case_id,)).fetchone()
    if scores:
        pdf.cell(200, 10, txt=f"Risk Score: {scores['risk_score']}", ln=1, align='L')
        pdf.cell(200, 10, txt=f"Anomaly Score: {scores['anomaly_score']}", ln=1, align='L')

    report = conn.execute("SELECT * FROM gemma_reports WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
    if report:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', size=12)
        pdf.cell(200, 10, txt="AI Compliance Report", ln=1)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 10, txt=f"What Happened: {report['what_happened']}")
        pdf.multi_cell(0, 10, txt=f"Why It Matters: {report['why_it_matters']}")
        pdf.multi_cell(0, 10, txt=f"Recommended Action: {report['recommended_action']}")

    pdf.ln(5)
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Audit Trail", ln=1)
    pdf.set_font("Arial", size=10)
    
    audit_logs = conn.execute("SELECT * FROM audit_log WHERE case_id = ? ORDER BY event_time ASC", (case_id,)).fetchall()
    for log in audit_logs:
        pdf.multi_cell(0, 8, txt=f"[{log['event_time']}] {log['reviewer_action']}: {log['notes']}")

    conn.close()
    
    os.makedirs('exports', exist_ok=True)
    file_path = f"exports/EXPORT_{case_id}_{tenant_id}.pdf"
    pdf.output(file_path)
    
    # Hash the file
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    file_hash = hasher.hexdigest()
    
    # Log the export
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute("INSERT OR IGNORE INTO audit_exports (export_id, tenant_id, case_ids, export_format, exported_at, file_path, file_hash, includes_full_provenance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (f"EXP_{case_id}_{int(datetime.now().timestamp())}", tenant_id, case_id, "PDF", datetime.utcnow().isoformat(), file_path, file_hash, 1))
    conn.commit()
    conn.close()

    return {"status": "success", "file_path": file_path, "file_hash": file_hash}

if __name__ == '__main__':
    init_provenance_tables()
    print("Enhanced audit export module initialized.")

def verify_case_reproducibility(case_id, tenant_id):
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    prov = conn.execute("SELECT * FROM provenance_chains WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
    conn.close()
    if prov:
        return {"verified": bool(prov['reproducible']), "provenance_id": prov['provenance_id']}
    return {"verified": False, "message": "No provenance found"}

def create_case_snapshot(case_id, tenant_id):
    import uuid
    prov_id = str(uuid.uuid4())
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.execute("INSERT OR IGNORE INTO provenance_chains (provenance_id, tenant_id, case_id, snapshot_timestamp) VALUES (?, ?, ?, ?)", (prov_id, tenant_id, case_id, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"snapshot": prov_id}

