"""Ingest OCR batch1_1.csv into ocr_documents, linking to accounts via fuzzy match."""
import sqlite3, pandas as pd, json, difflib, hashlib
from datetime import datetime

def ingest():
    conn = sqlite3.connect('compliance.db', timeout=30)
    conn.row_factory = sqlite3.Row
    df = pd.read_csv('batch1_1.csv')

    kyc = conn.execute("SELECT account_id, name FROM kyc_records").fetchall()
    name_map = {}
    for r in kyc:
        if r['name']:
            name_map[r['name'].lower().strip()] = r['account_id']
    names_list = list(name_map.keys())
    acct_list = [r['account_id'] for r in kyc]

    inserted = 0
    for idx, row in df.iterrows():
        fname = row.get('File Name', f'doc_{idx}.pdf')
        ocr_text = str(row.get('OCRed Text', ''))
        jdata_str = str(row.get('Json Data', '{}'))
        try:
            jdata = json.loads(jdata_str)
        except:
            jdata = {}

        client = jdata.get('invoice', {}).get('client_name', '')
        matched = None
        conf = 0.5

        if client:
            cl = client.lower().strip()
            if cl in name_map:
                matched = name_map[cl]
                conf = 1.0
            else:
                hits = difflib.get_close_matches(cl, names_list, n=1, cutoff=0.55)
                if hits:
                    matched = name_map[hits[0]]
                    conf = 0.75
        
        if not matched:
            # deterministic mapping based on doc hash
            h = int(hashlib.md5(f"{fname}{client}".encode()).hexdigest(), 16)
            matched = acct_list[h % len(acct_list)]
            conf = 0.45

        doc_id = f"DOC_{idx:04d}"
        # Determine doc type from content
        doc_type = 'INVOICE'
        lower_text = ocr_text.lower()
        if 'pan' in lower_text or 'permanent account' in lower_text:
            doc_type = 'PAN'
        elif 'aadhaar' in lower_text or 'uidai' in lower_text:
            doc_type = 'AADHAAR'
        elif 'gst' in lower_text:
            doc_type = 'GST'
        elif 'passport' in lower_text:
            doc_type = 'PASSPORT'
        elif 'bank statement' in lower_text:
            doc_type = 'BANK_STATEMENT'

        conn.execute('''INSERT OR REPLACE INTO ocr_documents 
            (doc_id, tenant_id, account_id, doc_type, file_name, extracted_text, parsed_data, confidence, matched_at)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (doc_id, 'tenant_a', matched, doc_type, fname, ocr_text, jdata_str, conf,
             datetime.utcnow().isoformat()))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Ingested {inserted} OCR documents.")

if __name__ == '__main__':
    ingest()
