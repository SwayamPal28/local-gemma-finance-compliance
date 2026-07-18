import sqlite3
import json
import os
from ocr_extract import extract_kyc_data

DB_PATH = 'compliance.db'

def check_consistency(case_id):
    account_id = case_id.replace('CASE_', '')
    conn = sqlite3.connect(DB_PATH, timeout=10)
    
    row = conn.execute('SELECT AVG(amount) as avg_amt, SUM(amount) as total_vol, COUNT(*) as tx_count, MAX(amount) as max_amt FROM transactions WHERE sender_id = ?', (account_id,)).fetchone()
    tx_count = row[2] if row else 0
    avg_tx = row[0] if row and row[0] else 0
    total_vol = row[1] if row and row[1] else 0
    max_amt = row[3] if row and row[3] else 0
    
    kyc_row = conn.execute('SELECT name, employer, declared_purpose, declared_income, ocr_confidence, id_number, account_type, dob, address FROM kyc_records WHERE account_id = ?', (account_id,)).fetchone()
    
    if not kyc_row:
        kyc_data = extract_kyc_data(account_id)
        if not kyc_data:
            conn.close()
            return {'mismatches': [{'message': 'No KYC record/image found for this account.', 'has_kyc': False}]}
            
        name = kyc_data.get('name', 'N/A')
        employer = kyc_data.get('employer', '')
        declared_purpose = kyc_data.get('declared_purpose', '')
        income = 0
        raw_income = kyc_data.get('declared_income', 0)
        
        if isinstance(raw_income, str):
            try:
                income = float(raw_income.replace('$', '').replace(',', '').strip())
            except:
                income = 0 if not raw_income else 0
        else:
            income = raw_income if raw_income else 0
            
        ocr_conf = 0.5
        id_number = ''
        account_type = 'Personal'
        dob = ''
        address = ''
    else:
        name = kyc_row[0] if kyc_row[0] else 'N/A'
        employer = kyc_row[1] if kyc_row[1] else ''
        declared_purpose = kyc_row[2] if kyc_row[2] else ''
        income = kyc_row[3] if kyc_row[3] else 0
        ocr_conf = kyc_row[4] if kyc_row[4] else 0
        id_number = kyc_row[5] if kyc_row[5] else ''
        account_type = kyc_row[6] if kyc_row[6] else 'Personal'
        dob = kyc_row[7] if kyc_row[7] else ''
        address = kyc_row[8] if kyc_row[8] else ''
        
    mismatches = []
    kyc_status = 'Verified' if ocr_conf >= 0.7 and id_number else 'Unverified'
    
    if ocr_conf < 0.6:
        severity = 'High' if ocr_conf < 0.4 else 'Medium'
        mismatches.append({
            'message': f'KYC verification incomplete: OCR confidence is {ocr_conf:.0%} (threshold: 60%). Documents may be illegible or tampered.',
            'evidence': {'field': 'ocr_confidence', 'severity': severity, 'category': 'Compliance'}
        })
        
    if not id_number:
        mismatches.append({
            'message': 'No government-issued ID number on file. Identity verification incomplete.',
            'evidence': {'field': 'id_number', 'severity': 'High', 'category': 'Compliance'}
        })
        
    if not dob:
        mismatches.append({
            'message': 'Date of birth not provided. Required for identity verification.',
            'evidence': {'field': 'dob', 'severity': 'Medium', 'category': 'Compliance'}
        })
        
    if not address or len(address) < 5:
        mismatches.append({
            'message': 'Address information is missing or incomplete.',
            'evidence': {'field': 'address', 'severity': 'Medium', 'category': 'Compliance'}
        })
        
    if income <= 0 and total_vol > 5000:
        mismatches.append({
            'message': f'Undeclared income: No income declared but ${total_vol:,.2f} in transaction volume detected.',
            'evidence': {'field': 'declared_income', 'severity': 'High', 'category': 'Compliance'}
        })
    elif income > 0 and total_vol > income * 5:
        ratio = total_vol / income
        mismatches.append({
            'message': f'Income mismatch: Declared income ${income:,.0f} but total volume is ${total_vol:,.2f} ({ratio:.1f}x income).',
            'evidence': {'field': 'declared_income', 'severity': 'High', 'category': 'Compliance'}
        })
    elif income > 0 and avg_tx > income * 0.5:
        mismatches.append({
            'message': f'Transaction size mismatch: Average transaction ${avg_tx:,.2f} exceeds 50% of declared income ${income:,.0f}.',
            'evidence': {'field': 'declared_income', 'severity': 'Medium', 'category': 'Operational'}
        })
        
    if declared_purpose in ('Personal Savings', 'Salary Account', 'Student Account'):
        if total_vol > 100000:
            mismatches.append({
                'message': f"Purpose mismatch: Declared '{declared_purpose}' but total volume is ${total_vol:,.2f}. Expected low-activity account.",
                'evidence': {'field': 'declared_purpose', 'severity': 'High', 'category': 'Compliance'}
            })
        elif total_vol > 50000:
            mismatches.append({
                'message': f"Purpose concern: Declared '{declared_purpose}' with ${total_vol:,.2f} volume - higher than typical for this account type.",
                'evidence': {'field': 'declared_purpose', 'severity': 'Medium', 'category': 'Operational'}
            })
            
    if declared_purpose in ('Personal Savings', 'Salary Account', 'Student Account') and tx_count > 30:
        mismatches.append({
            'message': f"Frequency mismatch: {tx_count} transactions for a '{declared_purpose}' account (expected < 30).",
            'evidence': {'field': 'declared_purpose', 'severity': 'High' if tx_count > 50 else 'Medium', 'category': 'Operational'}
        })
        
    if not employer or employer in ('Unknown', 'N/A', ''):
        if tx_count > 10:
            mismatches.append({
                'message': f'Employment unknown: No employer on record despite {tx_count} transactions. Source of funds unclear.',
                'evidence': {'field': 'employer', 'severity': 'Medium', 'category': 'Compliance'}
            })
            
    if account_type == 'Personal' and max_amt > 50000:
        mismatches.append({
            'message': f'Account type concern: Personal account with ${max_amt:,.0f} max transaction. May warrant Business account classification.',
            'evidence': {'field': 'account_type', 'severity': 'Medium', 'category': 'Operational'}
        })
        
    conn.close()
    
    return {
        'kyc_status': kyc_status,
        'profile': {
            'name': name,
            'employer': employer,
            'declared_purpose': declared_purpose,
            'declared_income': income,
            'account_type': account_type
        },
        'mismatches': mismatches,
        'has_kyc': True
    }
