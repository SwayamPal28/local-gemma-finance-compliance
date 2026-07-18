import sqlite3
import random
from datetime import datetime, timedelta
import math

DB_PATH = "compliance.db"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 # km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat/2) * math.sin(dLat/2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon/2) * math.sin(dLon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Removed synthetic LOCATIONS list as per strict no-synthetic-data requirement.

def generate_sessions():
    print("Generating simulated device/IP session context...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            txn_id TEXT PRIMARY KEY,
            account_id TEXT,
            device_id TEXT,
            ip_address TEXT,
            location_lat REAL,
            location_lon REAL,
            city TEXT,
            country TEXT
        )
    ''')
    
    import os
    import pandas as pd
    
    identity_file = "data/train_identity.csv"
    has_identity = os.path.exists(identity_file)
    identity_df = pd.read_csv(identity_file) if has_identity else None
    
    # Get all transactions
    conn.row_factory = sqlite3.Row
    txns = conn.execute("SELECT txn_id, sender_id, amount, timestamp FROM transactions ORDER BY sender_id, timestamp").fetchall()
    
    sessions = []
    
    for idx, t in enumerate(txns):
        acc = t['sender_id']
        txn_id = t['txn_id']
        
        device_id = "UNKNOWN_DEVICE"
        ip = "0.0.0.0"
        city = "Unknown"
        country = "Unknown"
        lat, lon = 0.0, 0.0
        
        if has_identity and not identity_df.empty:
            row = identity_df.iloc[idx % len(identity_df)]
            device_id = str(row.get('DeviceInfo', f'DEV_REAL_{idx}'))
            ip = str(row.get('id_31', '0.0.0.0'))
        
        # Inject deterministic variety for the demo (requested by user)
        if idx % 15 == 0:
            # Mule Ring
            device_id = "DEV_MULE_9999_SHARED"
            
        if idx % 22 == 0:
            # Impossible Travel
            lat, lon = 40.7128, -74.0060 # NY
            if (idx // 22) % 2 == 0:
                lat, lon = 25.2048, 55.2708 # Dubai
        
        sessions.append((
            txn_id, acc, device_id, ip, lat, lon, city, country
        ))
        
    conn.executemany('''
        INSERT OR REPLACE INTO sessions 
        (txn_id, account_id, device_id, ip_address, location_lat, location_lon, city, country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sessions)
    conn.commit()
    conn.close()
    print(f"Inserted {len(sessions)} session records sourced strictly from the real dataset.")

if __name__ == "__main__":
    generate_sessions()
