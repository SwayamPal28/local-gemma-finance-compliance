import sqlite3
import pandas as pd
import uuid
import datetime
import random
import hashlib
import json

# ── City database with lat/lon for realistic geo data ──
CITIES = [
    {"city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060, "isp": "Verizon", "asn": "AS701"},
    {"city": "Los Angeles", "country": "US", "lat": 34.0522, "lon": -118.2437, "isp": "AT&T", "asn": "AS7018"},
    {"city": "Chicago", "country": "US", "lat": 41.8781, "lon": -87.6298, "isp": "Comcast", "asn": "AS7922"},
    {"city": "Houston", "country": "US", "lat": 29.7604, "lon": -95.3698, "isp": "Spectrum", "asn": "AS11427"},
    {"city": "Miami", "country": "US", "lat": 25.7617, "lon": -80.1918, "isp": "AT&T", "asn": "AS7018"},
    {"city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278, "isp": "BT Group", "asn": "AS2856"},
    {"city": "Frankfurt", "country": "DE", "lat": 50.1109, "lon": 8.6821, "isp": "Deutsche Telekom", "asn": "AS3320"},
    {"city": "Paris", "country": "FR", "lat": 48.8566, "lon": 2.3522, "isp": "Orange S.A.", "asn": "AS5511"},
    {"city": "Singapore", "country": "SG", "lat": 1.3521, "lon": 103.8198, "isp": "SingTel", "asn": "AS9506"},
    {"city": "Dubai", "country": "AE", "lat": 25.2048, "lon": 55.2708, "isp": "Etisalat", "asn": "AS8966"},
    {"city": "Mumbai", "country": "IN", "lat": 19.0760, "lon": 72.8777, "isp": "Reliance Jio", "asn": "AS55836"},
    {"city": "Bengaluru", "country": "IN", "lat": 12.9716, "lon": 77.5946, "isp": "Airtel", "asn": "AS9498"},
    {"city": "Tokyo", "country": "JP", "lat": 35.6762, "lon": 139.6503, "isp": "NTT", "asn": "AS2914"},
    {"city": "Hong Kong", "country": "HK", "lat": 22.3193, "lon": 114.1694, "isp": "PCCW", "asn": "AS4760"},
    {"city": "Sydney", "country": "AU", "lat": -33.8688, "lon": 151.2093, "isp": "Telstra", "asn": "AS1221"},
    {"city": "São Paulo", "country": "BR", "lat": -23.5505, "lon": -46.6333, "isp": "Vivo", "asn": "AS26615"},
    {"city": "Toronto", "country": "CA", "lat": 43.6532, "lon": -79.3832, "isp": "Bell Canada", "asn": "AS577"},
    {"city": "Zurich", "country": "CH", "lat": 47.3769, "lon": 8.5417, "isp": "Swisscom", "asn": "AS3303"},
    {"city": "Amsterdam", "country": "NL", "lat": 52.3676, "lon": 4.9041, "isp": "KPN", "asn": "AS1136"},
    {"city": "Moscow", "country": "RU", "lat": 55.7558, "lon": 37.6173, "isp": "Rostelecom", "asn": "AS12389"},
    {"city": "Lagos", "country": "NG", "lat": 6.5244, "lon": 3.3792, "isp": "MTN Nigeria", "asn": "AS29465"},
    {"city": "Nairobi", "country": "KE", "lat": -1.2921, "lon": 36.8219, "isp": "Safaricom", "asn": "AS33771"},
    {"city": "Panama City", "country": "PA", "lat": 8.9824, "lon": -79.5199, "isp": "Cable & Wireless", "asn": "AS11556"},
    {"city": "Cayman Islands", "country": "KY", "lat": 19.3133, "lon": -81.2546, "isp": "LIME", "asn": "AS7303"},
]

FIRST_NAMES = ["James", "Maria", "Robert", "Linda", "Michael", "Sarah", "David", "Jennifer", "William", "Patricia",
               "Richard", "Elizabeth", "Joseph", "Susan", "Thomas", "Jessica", "Christopher", "Margaret", "Daniel", "Dorothy",
               "Raj", "Priya", "Chen", "Wei", "Yuki", "Amir", "Fatima", "Omar", "Sofia", "Alessandro"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Patel", "Kumar", "Singh", "Wang", "Li", "Chen", "Nakamura", "Al-Rashid", "Rossi", "Mueller"]

EMPLOYERS = ["Goldman Sachs", "JPMorgan Chase", "Morgan Stanley", "HSBC Holdings", "Deutsche Bank", "UBS Group",
             "Barclays PLC", "Credit Suisse", "BNP Paribas", "Citigroup", "Wells Fargo", "Bank of America",
             "TechVentures LLC", "Global Trade Co.", "Horizon Imports", "Summit Capital", "Apex Financial",
             "Pacific Rim Trading", "Nordic Solutions AB", "Mediterranean Exports", "Self-Employed", "Freelancer",
             "Atlas Logistics", "Quantum Holdings", "Vanguard Industries"]

PURPOSES = ["Personal Savings", "Business Operations", "International Trade", "Investment Portfolio", 
            "Payroll Processing", "Real Estate", "Import/Export", "Consulting Fees", "Family Support",
            "Cryptocurrency Trading", "E-Commerce Revenue", "Rental Income"]

BROWSERS = ["Chrome 125", "Firefox 128", "Safari 18", "Edge 125", "Chrome 124", "Firefox 127", "Opera 111"]
OS_LIST = ["Windows 11", "macOS 15", "Windows 10", "Ubuntu 24.04", "iOS 18", "Android 15", "macOS 14"]
DEVICE_TYPES = ["Desktop", "Laptop", "Mobile", "Tablet"]

def _gen_ip():
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def _gen_device_fingerprint(seed):
    return hashlib.sha256(seed.encode()).hexdigest()[:16]

def _gen_device_id(seed):
    return f"DEV_{hashlib.md5(seed.encode()).hexdigest()[:12].upper()}"

def load_data():
    conn = sqlite3.connect('compliance.db')
    
    # 1. Clear existing data
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM case_scores")
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM kyc_records")
    
    # Ensure sessions table has all needed columns
    existing_cols = [c[1] for c in conn.execute('PRAGMA table_info(sessions)').fetchall()]
    new_cols = {
        'browser': 'TEXT', 'os': 'TEXT', 'device_type': 'TEXT', 
        'device_fingerprint': 'TEXT', 'isp': 'TEXT', 'asn': 'TEXT',
        'is_vpn_or_proxy': 'INTEGER DEFAULT 0', 'country': 'TEXT',
        'receiver_country': 'TEXT'
    }
    for col, dtype in new_cols.items():
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {dtype}")
            except Exception:
                pass
    
    conn.commit()
    
    # 2. Load Real Data from HI-Small_Trans.csv
    print("Reading HI-Small_Trans.csv...")
    df = pd.read_csv('HI-Small_Trans.csv', nrows=25000)
    
    print("Populating transactions...")
    transactions_to_insert = []
    laundering_senders = set()
    high_value_senders = set()
    normal_senders = set()
    
    # Track transaction details per account for session enrichment
    txn_details_by_account = {}

    for i, row in df.iterrows():
        txn_id = str(uuid.uuid4())
        sender_id = str(row['Account']).strip()
        receiver_id = str(row['Account.1']).strip()
        amount = float(row['Amount Paid'])
        ts_raw = str(row['Timestamp'])
        try:
            ts = datetime.datetime.strptime(ts_raw, '%Y/%m/%d %H:%M').isoformat() + "Z"
        except Exception:
            ts = ts_raw
            
        txn_type = str(row['Payment Format'])
        label = int(row['Is Laundering'])
        
        transactions_to_insert.append((
            txn_id, 'tenant_a', sender_id, receiver_id, amount, ts, txn_type, label
        ))
        
        txn_details_by_account.setdefault(sender_id, []).append({
            'txn_id': txn_id, 'receiver': receiver_id, 'amount': amount,
            'ts': ts, 'type': txn_type, 'label': label, 'direction': 'outbound'
        })
        txn_details_by_account.setdefault(receiver_id, []).append({
            'txn_id': txn_id, 'sender': sender_id, 'amount': amount,
            'ts': ts, 'type': txn_type, 'label': label, 'direction': 'inbound'
        })
        
        if label == 1:
            laundering_senders.add(sender_id)
        elif amount > 25000:
            high_value_senders.add(sender_id)
        else:
            normal_senders.add(sender_id)
            
    conn.executemany("""
        INSERT INTO transactions (txn_id, tenant_id, sender_id, receiver_id, amount, timestamp, type, label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, transactions_to_insert)
    
    cases_to_create = list(set(list(laundering_senders)[:15] + list(high_value_senders)[:15] + list(normal_senders)[:20]))
    
    print(f"Creating {len(cases_to_create)} cases (laundering, high-value, normal)...")
    cases_data = []
    sessions_data = []
    kyc_data = []
    
    # Pre-assign shared devices for mule ring detection (laundering accounts share devices)
    laundering_list = [a for a in cases_to_create if a in laundering_senders]
    shared_devices = {}
    if len(laundering_list) >= 2:
        # Group some laundering accounts to share devices
        for i in range(0, min(6, len(laundering_list)), 2):
            if i + 1 < len(laundering_list):
                shared_dev = _gen_device_id(f"shared_mule_{i}")
                shared_devices[laundering_list[i]] = shared_dev
                shared_devices[laundering_list[i+1]] = shared_dev
    
    for idx, account_id in enumerate(cases_to_create):
        case_id = f"CASE_{account_id}"
        is_laundering = account_id in laundering_senders
        is_high_value = account_id in high_value_senders
        
        # Generate realistic anomaly score based on account category
        if is_laundering:
            anomaly_score = random.uniform(0.75, 0.99)
        elif is_high_value:
            anomaly_score = random.uniform(0.40, 0.70)
        else:
            anomaly_score = random.uniform(0.05, 0.35)
            
        cases_data.append((
            case_id, 'tenant_a', account_id, anomaly_score, anomaly_score, '{}', '{}', 'OPEN', 
            None, random.uniform(100.0, 5000.0), 'Triage'
        ))
        
        # ── Generate realistic per-account devices ──
        if is_laundering:
            num_devices = random.randint(2, 4)
            num_cities = random.randint(3, 6)  # Multi-city for impossible travel
            use_vpn = random.random() < 0.6
        elif is_high_value:
            num_devices = random.randint(1, 3)
            num_cities = random.randint(2, 3)
            use_vpn = random.random() < 0.2
        else:
            num_devices = random.randint(1, 2)
            num_cities = 1
            use_vpn = False
        
        # Assign cities
        account_cities = random.sample(CITIES, min(num_cities, len(CITIES)))
        home_city = account_cities[0]
        
        # Assign devices
        devices = []
        for d in range(num_devices):
            dev_seed = f"{account_id}_dev_{d}"
            dev_id = shared_devices.get(account_id, _gen_device_id(dev_seed)) if d == 0 else _gen_device_id(dev_seed)
            devices.append({
                'device_id': dev_id,
                'fingerprint': _gen_device_fingerprint(dev_seed),
                'browser': random.choice(BROWSERS),
                'os': random.choice(OS_LIST),
                'device_type': random.choice(DEVICE_TYPES),
            })
        
        # Create sessions for each transaction this account is involved in
        account_txns = txn_details_by_account.get(account_id, [])
        # Sort by timestamp and limit
        account_txns.sort(key=lambda x: x['ts'])
        account_txns = account_txns[:50]  # Cap per account
        
        for t_idx, txn in enumerate(account_txns):
            city_info = account_cities[t_idx % len(account_cities)] if is_laundering else home_city
            if is_high_value and t_idx > 0 and random.random() < 0.3:
                city_info = random.choice(account_cities)
            
            device = devices[t_idx % len(devices)]
            ip = _gen_ip()
            is_vpn = 1 if (use_vpn and t_idx > 0 and random.random() < 0.4) else 0
            
            # Determine receiver country
            receiver_acc = txn.get('receiver', txn.get('sender', ''))
            receiver_city = random.choice(CITIES)
            
            sessions_data.append((
                str(uuid.uuid4()),   # session_id
                'tenant_a',          # tenant_id
                account_id,          # account_id
                txn['txn_id'],       # txn_id
                device['device_id'], # device_id
                ip,                  # ip_address
                city_info['city'],   # city
                city_info['lat'] + random.uniform(-0.01, 0.01),   # location_lat
                city_info['lon'] + random.uniform(-0.01, 0.01),   # location_lon
                txn['ts'],           # timestamp
                device['browser'],   # browser
                device['os'],        # os
                device['device_type'], # device_type
                device['fingerprint'], # device_fingerprint
                city_info['isp'],    # isp
                city_info['asn'],    # asn
                is_vpn,              # is_vpn_or_proxy
                city_info['country'], # country
                receiver_city['country']  # receiver_country
            ))
        
        # ── Generate realistic KYC data ──
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        employer = random.choice(EMPLOYERS)
        purpose = random.choice(PURPOSES)
        
        if is_laundering:
            income = random.randint(30000, 80000)  # Declared low vs actual high activity
            ocr_conf = random.uniform(0.4, 0.75)   # Lower OCR confidence
        elif is_high_value:
            income = random.randint(150000, 500000)
            ocr_conf = random.uniform(0.8, 0.98)
        else:
            income = random.randint(40000, 120000)
            ocr_conf = random.uniform(0.85, 0.99)
        
        dob = f"{random.randint(1960, 2000)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        address = f"{random.randint(1, 9999)} {random.choice(['Main St', 'Oak Ave', 'Pine Rd', 'Elm Dr', 'Market St', 'Broadway', 'Park Ave'])}, {home_city['city']}"
        
        kyc_data.append((
            account_id, name, employer, purpose, float(income),
            ocr_conf, f"ID{random.randint(100000, 999999)}", 
            random.choice(['Personal', 'Business', 'Joint']),
            dob, address
        ))

    conn.executemany("""
        INSERT INTO case_scores (case_id, tenant_id, account_id, anomaly_score, risk_score, risk_dimensions, rule_flags, status, graph_flags, expected_roi, assigned_queue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cases_data)
    
    conn.executemany("""
        INSERT INTO sessions (session_id, tenant_id, account_id, txn_id, device_id, ip_address, city, location_lat, location_lon, timestamp, browser, os, device_type, device_fingerprint, isp, asn, is_vpn_or_proxy, country, receiver_country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sessions_data)
    
    conn.executemany("""
        INSERT INTO kyc_records (account_id, name, employer, declared_purpose, declared_income, ocr_confidence, id_number, account_type, dob, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, kyc_data)
    
    conn.commit()
    conn.close()
    print("Real data loaded successfully.")

if __name__ == '__main__':
    load_data()
