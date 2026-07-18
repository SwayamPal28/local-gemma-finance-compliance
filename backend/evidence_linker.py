import json
import sqlite3
import os

DB_PATH = 'compliance.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def generate_evidence_links(case_id, rule_flags):
    """
    Correlates rules triggered with specific document fields.
    For simplicity, we map known rules to simulated bounding boxes and page numbers.
    In a real implementation, this would cross-reference with OCR outputs and multimodal data.
    """
    evidence_links = []
    
    # Pre-defined mapping of rule types to likely visual regions
    # In a full system, this would come dynamically from multimodal_processor.py outputs
    rule_evidence_map = {
        'Large Transaction': {'bbox': [100, 200, 300, 250], 'page': 1, 'field': 'amount'},
        'Structuring': {'bbox': [100, 300, 300, 400], 'page': 1, 'field': 'transaction_history'},
        'Mule Ring (Shared Device)': {'bbox': [50, 50, 400, 100], 'page': 2, 'field': 'device_fingerprint'},
        'Impossible Travel': {'bbox': [50, 150, 400, 200], 'page': 2, 'field': 'login_location'},
        'High Velocity': {'bbox': [100, 400, 300, 500], 'page': 1, 'field': 'transaction_volume'}
    }

    for idx, flag in enumerate(rule_flags):
        rule_name = flag.get('rule')
        mapping = rule_evidence_map.get(rule_name, {'bbox': [0, 0, 0, 0], 'page': 1, 'field': 'unknown'})
        
        evidence_links.append({
            'flag_index': idx,
            'rule': rule_name,
            'evidence': {
                'document_type': 'Account Statement',
                'page_number': mapping['page'],
                'bounding_box': mapping['bbox'],
                'matched_record': flag.get('reason'),
                'highlight_region': mapping['field']
            }
        })
        
    return evidence_links

def get_audit_provenance(case_id, tenant_id):
    """
    Retrieves the complete chain showing exactly why a case was flagged.
    """
    conn = get_db()
    try:
        case = conn.execute("SELECT rule_flags FROM case_scores WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
        if not case:
            return {"status": "error", "message": "Case not found"}
        
        rule_flags = json.loads(case['rule_flags']) if case['rule_flags'] else []
        evidence_links = generate_evidence_links(case_id, rule_flags)
        
        return {
            "case_id": case_id,
            "tenant_id": tenant_id,
            "provenance_chain": evidence_links
        }
    finally:
        conn.close()
